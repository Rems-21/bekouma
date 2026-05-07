import io
import os
import uuid
from datetime import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, FileResponse
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
import reportlab.platypus.flowables
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from .models import Contract
from cart.models import Order
from blockchain.utils import record_transaction
from accounts.models import Notification

@login_required
def generate_contract(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    
    if order.status != 'paid':
        return redirect('accounts:dashboard')
    
    contract, created = Contract.objects.get_or_create(
        order=order,
        user=request.user,
        defaults={
            'contract_number': f"CTR-{order.pk}-{uuid.uuid4().hex[:6].upper()}",
        }
    )
    
    if created or not contract.pdf_file:
        pdf_buffer = generate_pdf(order, contract)
        filename = f"contrat_{contract.contract_number}.pdf"
        from django.core.files.base import ContentFile
        contract.pdf_file.save(filename, ContentFile(pdf_buffer.getvalue()))
        
        block = record_transaction('contract_generated', {
            'contract_number': contract.contract_number,
            'order_id': order.pk,
            'user': request.user.username,
            'amount': order.total_amount,
        })
        contract.blockchain_hash = block.hash
        contract.save()
        
        Notification.objects.create(
            user=request.user,
            notification_type='system',
            title='Contrat généré',
            message=f'Votre contrat {contract.contract_number} est prêt. Vous pouvez le télécharger.',
            link=f'/contrats/{contract.pk}/download/',
        )
    
    return render(request, 'contracts/view.html', {
        'contract': contract,
        'order': order,
    })

@login_required
def download_contract(request, pk):
    contract = get_object_or_404(Contract, pk=pk, user=request.user)
    if contract.pdf_file:
        return FileResponse(contract.pdf_file.open('rb'), content_type='application/pdf', as_attachment=True, filename=f"contrat_{contract.contract_number}.pdf")
    return redirect('contracts:generate', order_id=contract.order.pk)

class _FillSpacer(reportlab.platypus.flowables.Flowable):
    """Takes remaining space minus reserve for what follows, keeping everything on one page."""
    def __init__(self, reserve=4*cm):
        super().__init__()
        self._reserve = reserve
    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        usable = availHeight - self._reserve
        self.height = max(0, usable)
        return (self.width, self.height)
    def draw(self):
        pass


def generate_pdf(order, contract):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
    )

    styles = getSampleStyleSheet()
    navy = colors.HexColor('#1C2331')
    gold = colors.HexColor('#E8A317')

    s_head = ParagraphStyle('H', parent=styles['Normal'], fontSize=10, textColor=gold, fontName='Helvetica-Bold', spaceAfter=6, spaceBefore=10)
    s_norm = ParagraphStyle('N', parent=styles['Normal'], fontSize=9, spaceAfter=3, spaceBefore=0, leading=13)
    s_cond = ParagraphStyle('Cd', parent=styles['Normal'], fontSize=8.5, spaceAfter=3, spaceBefore=0, leading=12)

    user = order.user
    elements = []

    # ---- En-tête avec logo ----
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
    logo_cell = ''
    if os.path.exists(logo_path):
        logo_cell = Image(logo_path, width=2.2*cm, height=2.2*cm)

    header_left = Paragraph(
        "<b>RAOLY BTP</b><br/><font size='8' color='#666666'>Location de Matériels de Chantier</font>",
        ParagraphStyle('TL', parent=styles['Normal'], fontSize=15, textColor=navy, fontName='Helvetica-Bold', leading=18)
    )
    header_right = Paragraph(
        f"<b>CONTRAT N° {contract.contract_number}</b><br/>"
        f"Date : {datetime.now().strftime('%d/%m/%Y')}<br/>"
        f"Réf. commande : #{order.pk}",
        ParagraphStyle('TR', parent=s_norm, alignment=TA_RIGHT)
    )

    ht = Table([[logo_cell, header_left, header_right]], colWidths=[2.6*cm, 8.4*cm, 6*cm])
    ht.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW', (0, 0), (-1, 0), 2, gold),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
    ]))
    elements.append(ht)
    elements.append(Spacer(1, 14))

    # ---- Locataire + Période ----
    client_info = (
        f"<b>Nom :</b> {user.get_full_name() or user.username}<br/>"
        f"<b>Email :</b> {user.email}<br/>"
        f"<b>Tél :</b> {user.phone}"
    )
    if user.company_name:
        client_info += f"<br/><b>Entreprise :</b> {user.company_name}"
    if user.address:
        client_info += f"<br/><b>Adresse :</b> {user.address}"

    period_info = (
        f"<b>Date de prise :</b> {order.rental_date.strftime('%d/%m/%Y') if order.rental_date else 'N/A'}<br/>"
        f"<b>Date de retour :</b> {order.return_date.strftime('%d/%m/%Y') if order.return_date else 'N/A'}"
    )

    info_data = [[
        [Paragraph("LOCATAIRE", s_head), Paragraph(client_info, s_norm)],
        [Paragraph("PÉRIODE", s_head), Paragraph(period_info, s_norm)],
    ]]
    info_table = Table(info_data, colWidths=[9.5*cm, 7.5*cm])
    info_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    elements.append(info_table)
    elements.append(Spacer(1, 10))

    # ---- Tableau des matériels ----
    elements.append(Paragraph("MATÉRIELS LOUÉS", s_head))
    table_data = [['Matériel', 'Qté', 'Prix/jour', 'Jours', 'Chauffeur', 'Total']]
    for res in order.reservations.all():
        driver_str = f"{res.driver_price:,} F" if res.with_driver else "—"
        daily_rate = res.equipment.daily_price_for_user(user)
        table_data.append([
            res.equipment.name,
            str(res.quantity),
            f"{daily_rate:,} F",
            str(res.num_days),
            driver_str,
            f"{res.total_price:,} F",
        ])
    table_data.append(['', '', '', '', 'TOTAL', f"{order.total_amount:,} FCFA"])

    table = Table(table_data, colWidths=[5*cm, 1.3*cm, 2.5*cm, 1.5*cm, 2.2*cm, 2.5*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), navy),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('BACKGROUND', (0, -1), (-1, -1), gold),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, -1), (-1, -1), navy),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F5F5F5')]),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))

    # ---- Emplacement(s) déclaré(s) ----
    declared_locations = []
    for res in order.reservations.all():
        if res.declared_location_name:
            declared_locations.append(f"{res.equipment.name}: {res.declared_location_name}")
    if declared_locations:
        elements.append(Paragraph("EMPLACEMENT(S) DÉCLARÉ(S)", s_head))
        for loc in declared_locations[:3]:
            elements.append(Paragraph(f"• {loc}", s_cond))
    else:
        elements.append(Paragraph("EMPLACEMENT(S) DÉCLARÉ(S)", s_head))
        elements.append(Paragraph("• Aucun emplacement spécifique déclaré au moment de la génération.", s_cond))
    elements.append(Spacer(1, 4))

    # ---- Conditions ----
    elements.append(Paragraph("CONDITIONS GÉNÉRALES", s_head))
    conds = [
        "1. Le matériel doit être restitué en bon état à la date de retour prévue.",
        "2. Retard de restitution : pénalité de 2% du montant total par jour de retard.",
        "3. Annulation : 3 jours avant → 90% remboursé · 2 jours → 50% · 1 jour ou moins → 0%.",
        "4. Le locataire est responsable de tout dommage causé au matériel.",
        "5. Utilisation conforme à la destination du matériel et aux normes de sécurité.",
        "6. L'engin doit être utilisé à l'emplacement déclaré par le locataire; usage hors zone déclarée: pénalité de 15% du montant total (minimum 50 000 FCFA).",
    ]
    for c in conds:
        elements.append(Paragraph(c, s_cond))

    # ---- Pousse les signatures en bas de page ----
    elements.append(_FillSpacer(reserve=4.5*cm))

    # ---- Signatures ----
    sig_data = [
        [Paragraph("<b>Le locataire</b>", ParagraphStyle('SL', parent=s_norm, alignment=TA_CENTER, fontSize=9)),
         Paragraph("<b>Pour RAOLY BTP</b>", ParagraphStyle('SR', parent=s_norm, alignment=TA_CENTER, fontSize=9))],
        ['', ''],
        [Paragraph(f"<i>{user.get_full_name() or user.username}</i>", ParagraphStyle('SN', parent=s_norm, alignment=TA_CENTER, fontSize=8)),
         Paragraph("<i>RAOLY BTP SAS</i>", ParagraphStyle('SC', parent=s_norm, alignment=TA_CENTER, fontSize=8))],
    ]
    sig_table = Table(sig_data, colWidths=[7.5*cm, 7.5*cm])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 35),
        ('LINEBELOW', (0, 1), (0, 1), 0.5, colors.black),
        ('LINEBELOW', (1, 1), (1, 1), 0.5, colors.black),
    ]))
    elements.append(sig_table)

    elements.append(Paragraph(
        f"Fait à Douala, le {datetime.now().strftime('%d/%m/%Y')}",
        ParagraphStyle('FD', parent=s_norm, alignment=TA_CENTER, textColor=colors.grey, fontSize=8, spaceBefore=6)
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer
