from django.db import models
from user.models import Account
# Create your models here.
class AccountCredentials(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    client_id = models.BinaryField()
    client_secret = models.BinaryField()

    

class EncryptionKeyId(models.Model):
    keyid = models.CharField(max_length=256)
    account = models.OneToOneField(Account, on_delete=models.CASCADE)
    