from fastapi import APIRouter, HTTPException
from prisma.models import Match, MatchPlayer, User

from core.models.match import MatchStats, PlayerStats

router = APIRouter(tags=["Matches"])


@router.get("/{match_id}/stats", response_model=MatchStats)
async def get_match_stats(match_id: str) -> MatchStats:
    """Get statistics for a specific match."""

    # Find match
    match = await Match.prisma().find_unique(where={"id": match_id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Calculate duration if available
    duration_seconds = None
    if match.startedAt and match.endedAt:
        duration_seconds = int((match.endedAt - match.startedAt).total_seconds())

    # Get players with related user data
    players_data = await MatchPlayer.prisma().find_many(where={"matchId": match_id})

    # Fetch usernames in parallel
    user_ids = [p.userId for p in players_data]
    users = await User.prisma().find_many(where={"id": {"in": user_ids}})
    username_map = {u.id: u.username for u in users}

    # Map to PlayerStats
    players = []
    for p in players_data:
        players.append(
            PlayerStats(
                user_id=p.userId,
                username=username_map.get(p.userId, "Unknown"),
                bombs_placed=p.bombsPlaced,
                players_killed=p.playersKilled,
                is_winner=p.isWinner,
            )
        )

    return MatchStats(
        match_id=match.id,
        winner_id=match.winnerUserId,
        players=players,
        duration_seconds=duration_seconds,
    )
