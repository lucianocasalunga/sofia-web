#!/usr/bin/env python3
"""
Script para deletar chats expirados automaticamente
Deve ser executado periodicamente via cron (recomendado: diariamente)

Adicionar ao crontab:
0 3 * * * cd /mnt/projetos/sofia-web && /usr/bin/python3 cleanup_expired_chats.py >> /mnt/projetos/sofia-web/logs/cleanup.log 2>&1
"""

from database import db
from datetime import datetime

def main():
    print(f"[{datetime.now()}] Iniciando limpeza de chats expirados...")

    try:
        count = db.delete_expired_chats()

        if count > 0:
            print(f"[{datetime.now()}] ✅ {count} chat(s) expirado(s) deletado(s)")
        else:
            print(f"[{datetime.now()}] ℹ️  Nenhum chat expirado encontrado")

    except Exception as e:
        print(f"[{datetime.now()}] ❌ Erro ao deletar chats: {e}")
        return 1

    return 0

if __name__ == '__main__':
    exit(main())
