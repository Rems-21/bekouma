from datetime import datetime
import json

from django.db import IntegrityError, transaction

from .models import Block


def get_last_block():
    return Block.objects.order_by('-index').first()


def create_genesis_block():
    """Crée le bloc genèse si absent (usage shell / admin). Sécurisé contre la double création."""
    with transaction.atomic():
        first = Block.objects.select_for_update().order_by('index').first()
        if first:
            return first
        block = Block(
            index=0,
            data={'message': 'Genesis Block - RAOLY BTP'},
            previous_hash='0' * 64,
        )
        block.hash = Block.calculate_hash(0, datetime.now(), block.data, block.previous_hash)
        try:
            block.save()
        except IntegrityError:
            return Block.objects.order_by('index').first()
        return block


def add_block(data):
    """
    Chaîne un nouveau bloc. Verrouillage du dernier bloc pour éviter les collisions d’index
    (webhook + retour navigateur, ou requêtes concurrentes).
    """
    with transaction.atomic():
        last = Block.objects.select_for_update().order_by('-index').first()
        if not last:
            genesis = Block(
                index=0,
                data={'message': 'Genesis Block - RAOLY BTP'},
                previous_hash='0' * 64,
            )
            genesis.hash = Block.calculate_hash(0, datetime.now(), genesis.data, genesis.previous_hash)
            try:
                genesis.save()
            except IntegrityError:
                pass
            last = Block.objects.select_for_update().order_by('-index').first()
        if not last:
            raise RuntimeError('Impossible d’initialiser la blockchain')

        new_index = last.index + 1
        previous_hash = last.hash
        ts = datetime.now()
        new_hash = Block.calculate_hash(new_index, ts, data, previous_hash)

        return Block.objects.create(
            index=new_index,
            data=data,
            previous_hash=previous_hash,
            hash=new_hash,
        )


def verify_chain():
    blocks = Block.objects.all().order_by('index')
    for i, block in enumerate(blocks):
        if i == 0:
            continue
        prev = blocks[i - 1]
        if block.previous_hash != prev.hash:
            return False, f'Block #{block.index} has invalid previous hash'
        expected = Block.calculate_hash(block.index, block.timestamp, block.data, block.previous_hash)
        if block.hash != expected:
            return False, f'Block #{block.index} has been tampered with'
    return True, 'Blockchain is valid'


def record_transaction(transaction_type, details):
    data = {
        'type': transaction_type,
        'details': details,
        'recorded_at': str(datetime.now()),
    }
    return add_block(data)
