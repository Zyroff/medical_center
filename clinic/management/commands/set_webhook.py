from django.core.management.base import BaseCommand
import requests

class Command(BaseCommand):
    def handle(self, *args, **options):
        token = "8565788967:AAEXokz57WER4zVcH2-3oHF2Lh3ckgULGA0"
        webhook_url = "https://yourdomain.com/telegram/webhook/"
        
        url = f"https://api.telegram.org/bot{token}/setWebhook"
        data = {"url": webhook_url}
        
        response = requests.post(url, json=data)
        print(response.json())