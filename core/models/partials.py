from prisma.models import Skin, User, UserStats

Skin.create_partial("SkinOut", exclude=["id"], exclude_relational_fields=True)
UserStats.create_partial(
    "UserStatsOut", exclude=["id", "userId", "updatedAt"], exclude_relational_fields=True
)
User.create_partial(
    "CurrentUser",
    exclude=["userSkins", "matchPlayers", "currentSkinId"],
    relations={"stats": "UserStatsOut", "currentSkin": "SkinOut"},
)
User.create_partial(
    "Opponent",
    exclude=[
        "password",
        "createdAt",
        "updatedAt",
        "lastLoginAt",
        "status",
        "userSkins",
        "matchPlayers",
        "currentSkinId",
        "currentSkin",
    ],
    relations={"stats": "UserStatsOut"},
)
