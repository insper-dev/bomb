/*
  Warnings:

  - You are about to drop the `MatchHistory` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `Skin` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `UserSkin` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `UserStats` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the column `powerupsCollected` on the `MatchPlayer` table. All the data in the column will be lost.
  - You are about to drop the column `skinUsed` on the `MatchPlayer` table. All the data in the column will be lost.
  - You are about to drop the column `survived` on the `MatchPlayer` table. All the data in the column will be lost.
  - You are about to drop the column `wallsDestroyed` on the `MatchPlayer` table. All the data in the column will be lost.
  - You are about to drop the column `currentSkinId` on the `User` table. All the data in the column will be lost.
  - You are about to drop the column `lastLoginAt` on the `User` table. All the data in the column will be lost.
  - You are about to drop the column `updatedAt` on the `User` table. All the data in the column will be lost.

*/
-- DropIndex
DROP INDEX "Skin_name_key";

-- DropIndex
DROP INDEX "UserSkin_userId_skinId_key";

-- DropIndex
DROP INDEX "UserStats_userId_key";

-- DropTable
PRAGMA foreign_keys=off;
DROP TABLE "MatchHistory";
PRAGMA foreign_keys=on;

-- DropTable
PRAGMA foreign_keys=off;
DROP TABLE "Skin";
PRAGMA foreign_keys=on;

-- DropTable
PRAGMA foreign_keys=off;
DROP TABLE "UserSkin";
PRAGMA foreign_keys=on;

-- DropTable
PRAGMA foreign_keys=off;
DROP TABLE "UserStats";
PRAGMA foreign_keys=on;

-- CreateTable
CREATE TABLE "Match" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "startedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "endedAt" DATETIME,
    "winnerUserId" TEXT
);

-- RedefineTables
PRAGMA defer_foreign_keys=ON;
PRAGMA foreign_keys=OFF;
CREATE TABLE "new_MatchPlayer" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "matchId" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "isWinner" BOOLEAN NOT NULL DEFAULT false,
    "bombsPlaced" INTEGER NOT NULL DEFAULT 0,
    "playersKilled" INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT "MatchPlayer_matchId_fkey" FOREIGN KEY ("matchId") REFERENCES "Match" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "MatchPlayer_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO "new_MatchPlayer" ("bombsPlaced", "id", "isWinner", "matchId", "playersKilled", "userId") SELECT "bombsPlaced", "id", "isWinner", "matchId", "playersKilled", "userId" FROM "MatchPlayer";
DROP TABLE "MatchPlayer";
ALTER TABLE "new_MatchPlayer" RENAME TO "MatchPlayer";
CREATE UNIQUE INDEX "MatchPlayer_matchId_userId_key" ON "MatchPlayer"("matchId", "userId");
CREATE TABLE "new_User" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "username" TEXT NOT NULL,
    "password" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "status" TEXT NOT NULL DEFAULT 'OFFLINE'
);
INSERT INTO "new_User" ("createdAt", "id", "password", "status", "username") SELECT "createdAt", "id", "password", "status", "username" FROM "User";
DROP TABLE "User";
ALTER TABLE "new_User" RENAME TO "User";
CREATE UNIQUE INDEX "User_username_key" ON "User"("username");
PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;
