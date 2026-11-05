"""Private output only: credentials are hashed in storage but still sensitive."""
import django, json
django.setup()
from accounts.models import User
rows=list(User.objects.order_by('pk').values('pk','username','password','email','role','is_staff','is_superuser'))
print(json.dumps(rows, sort_keys=True))
