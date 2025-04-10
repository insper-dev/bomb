-- CreateTable
CREATE TABLE "User" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "username" TEXT NOT NULL,
    "password" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "lastLoginAt" DATETIME,
    "status" TEXT NOT NULL DEFAULT 'OFFLINE',
    "currentSkinId" TEXT,
    CONSTRAINT "User_currentSkinId_fkey" FOREIGN KEY ("currentSkinId") REFERENCES "Skin" ("id") ON DELETE SET NULL ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "Skin" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "imageUrl" TEXT,
    "isDefault" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CreateTable
CREATE TABLE "UserSkin" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "userId" TEXT NOT NULL,
    "skinId" TEXT NOT NULL,
    "obtainedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "UserSkin_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "UserSkin_skinId_fkey" FOREIGN KEY ("skinId") REFERENCES "Skin" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "UserStats" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "userId" TEXT NOT NULL,
    "matchesPlayed" INTEGER NOT NULL DEFAULT 0,
    "matchesWon" INTEGER NOT NULL DEFAULT 0,
    "matchesLost" INTEGER NOT NULL DEFAULT 0,
    "bombsPlaced" INTEGER NOT NULL DEFAULT 0,
    "wallsDestroyed" INTEGER NOT NULL DEFAULT 0,
    "powerupsCollected" INTEGER NOT NULL DEFAULT 0,
    "playersKilled" INTEGER NOT NULL DEFAULT 0,
    "rankPoints" INTEGER NOT NULL DEFAULT 0,
    "highestWinStreak" INTEGER NOT NULL DEFAULT 0,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "UserStats_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "MatchHistory" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "startedAt" DATETIME NOT NULL,
    "endedAt" DATETIME NOT NULL,
    "duration" INTEGER NOT NULL,
    "mapName" TEXT,
    "gameMode" TEXT NOT NULL DEFAULT 'CLASSIC',
    "winnerUserId" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CreateTable
CREATE TABLE "MatchPlayer" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "matchId" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "isWinner" BOOLEAN NOT NULL DEFAULT false,
    "bombsPlaced" INTEGER NOT NULL DEFAULT 0,
    "wallsDestroyed" INTEGER NOT NULL DEFAULT 0,
    "powerupsCollected" INTEGER NOT NULL DEFAULT 0,
    "playersKilled" INTEGER NOT NULL DEFAULT 0,
    "survived" BOOLEAN NOT NULL DEFAULT false,
    "skinUsed" TEXT,
    CONSTRAINT "MatchPlayer_matchId_fkey" FOREIGN KEY ("matchId") REFERENCES "MatchHistory" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "MatchPlayer_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateIndex
CREATE UNIQUE INDEX "User_username_key" ON "User"("username");

-- CreateIndex
CREATE UNIQUE INDEX "User_email_key" ON "User"("email");

-- CreateIndex
CREATE UNIQUE INDEX "Skin_name_key" ON "Skin"("name");

-- CreateIndex
CREATE UNIQUE INDEX "UserSkin_userId_skinId_key" ON "UserSkin"("userId", "skinId");

-- CreateIndex
CREATE UNIQUE INDEX "UserStats_userId_key" ON "UserStats"("userId");

-- CreateIndex
CREATE UNIQUE INDEX "MatchPlayer_matchId_userId_key" ON "MatchPlayer"("matchId", "userId");
