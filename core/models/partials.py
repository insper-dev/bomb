from prisma.models import Skin, User, UserStats

Skin.create_partial("SkinOut", exclude=["id"], exclude_relational_fields=True)
UserStats.create_partial("UserStatsOut", exclude=["id", "userId"], exclude_relational_fields=True)
User.create_partial(
    "CurrentUser",
    exclude=["id", "userSkins", "matchPlayers", "currentSkinId"],
    relations={"stats": "UserStatsOut", "currentSkin": "SkinOut"},
)
