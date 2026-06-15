from axis.models import ContactMessage


def create_contact_message(**kwargs):
    defaults = {
        "email": "user@example.com",
        "message": "Mensagem de contato com conteudo suficiente.",
        "source": "axis",
    }
    defaults.update(kwargs)
    return ContactMessage.objects.create(**defaults)
