from prisma.models import User

User.create_partial("CurrentUser", exclude_relational_fields=True)
