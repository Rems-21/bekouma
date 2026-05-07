from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=True, label="Téléphone")
    first_name = forms.CharField(max_length=30, required=True, label="Prénom")
    last_name = forms.CharField(max_length=30, required=True, label="Nom")
    user_type = forms.ChoiceField(
        label="Type de compte",
        choices=CustomUser.USER_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial=CustomUser.USER_TYPE_PARTICULIER,
    )
    accept_personal_data_processing = forms.BooleanField(
        required=True,
        label=(
            'J’accepte le traitement de mes données personnelles dans le cadre de la création '
            'et de la gestion de mon compte (obligatoire).'
        ),
        error_messages={'required': 'Vous devez accepter le traitement des données pour vous inscrire.'},
    )

    class Meta:
        model = CustomUser
        fields = (
            'username',
            'email',
            'first_name',
            'last_name',
            'phone',
            'user_type',
            'password1',
            'password2',
        )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'accept_personal_data_processing':
                field.widget.attrs['class'] = 'form-check-input'
            elif name == 'user_type':
                field.widget.attrs['class'] = ''
            else:
                field.widget.attrs['class'] = 'form-control'

class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = (
            'first_name',
            'last_name',
            'email',
            'phone',
            'address',
            'user_type',
            'company_name',
            'profile_image',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'user_type' and self.instance.pk:
                if self.instance.kyc_status == CustomUser.KYC_APPROVED:
                    field.disabled = True
                    field.help_text = (
                        'Le type de compte ne peut pas être modifié après validation KYC.'
                    )
            field.widget.attrs['class'] = 'form-control'
        if 'user_type' in self.fields:
            self.fields['user_type'].widget.attrs['class'] = ''

    def clean(self):
        cleaned = super().clean()
        utype = cleaned.get('user_type') or self.instance.user_type
        if utype == CustomUser.USER_TYPE_ENTREPRISE:
            cname = (cleaned.get('company_name') or '').strip()
            if not cname:
                self.add_error('company_name', 'La raison sociale est obligatoire pour un compte entreprise.')
        return cleaned


class KycDocumentForm(forms.ModelForm):
    """Upload des pièces ; la soumission est gérée dans la vue."""

    accept_kyc_data_processing = forms.BooleanField(
        required=True,
        label=(
            'J’accepte le traitement de mes données personnelles et des pièces transmises aux fins '
            'de vérification d’identité (KYC), y compris leur conservation le temps nécessaire à '
            'cette vérification (obligatoire).'
        ),
        error_messages={
            'required': 'Vous devez accepter le traitement des données pour envoyer votre dossier.',
        },
    )

    class Meta:
        model = CustomUser
        fields = (
            'kyc_id_document',
            'kyc_id_back_document',
            'kyc_proof_of_address',
            'kyc_rc_document',
            'kyc_tax_document',
            'kyc_company_proof_of_address',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.instance
        for name, field in self.fields.items():
            if name == 'accept_kyc_data_processing':
                field.widget.attrs['class'] = 'form-check-input'
                continue
            field.widget.attrs['class'] = 'form-control'
            if user.user_type == CustomUser.USER_TYPE_PARTICULIER:
                if name.startswith('kyc_rc') or name in (
                    'kyc_tax_document',
                    'kyc_company_proof_of_address',
                ):
                    field.required = False
            else:
                if name in ('kyc_id_document', 'kyc_id_back_document', 'kyc_proof_of_address'):
                    field.required = False

    def _has(self, name):
        f = self.cleaned_data.get(name)
        if f:
            return True
        return bool(getattr(self.instance, name, None))

    def clean(self):
        cleaned = super().clean()
        user = self.instance
        if user.user_type == CustomUser.USER_TYPE_PARTICULIER:
            if not self._has('kyc_id_document'):
                self.add_error('kyc_id_document', 'Ce document est obligatoire.')
            if not self._has('kyc_id_back_document'):
                self.add_error('kyc_id_back_document', 'Ce document est obligatoire.')
            if not self._has('kyc_proof_of_address'):
                self.add_error('kyc_proof_of_address', 'Ce document est obligatoire.')
        else:
            if not self._has('kyc_rc_document'):
                self.add_error('kyc_rc_document', 'Ce document est obligatoire.')
            if not self._has('kyc_tax_document'):
                self.add_error('kyc_tax_document', 'Ce document est obligatoire.')
            if not self._has('kyc_company_proof_of_address'):
                self.add_error(
                    'kyc_company_proof_of_address',
                    'Ce document est obligatoire.',
                )
        return cleaned
