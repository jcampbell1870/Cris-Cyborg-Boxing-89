#include "CrisCyborgBoxingGameMode.h"

ACrisCyborgBoxingGameMode::ACrisCyborgBoxingGameMode()
{
	PrimaryActorTick.TickInterval = 0.016f;

	Player1 = nullptr;
	Player2 = nullptr;
	CurrentGameState = EGameState::MainMenu;
	CurrentRound = 1;
	RoundDuration = 120.0f; // 2 minutes per round
	RoundTimeRemaining = RoundDuration;
	MatchWinner = nullptr;
}

void ACrisCyborgBoxingGameMode::BeginPlay()
{
	Super::BeginPlay();
}

void ACrisCyborgBoxingGameMode::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	if (CurrentGameState == EGameState::InMatch)
	{
		UpdateRoundTimer();
		CheckMatchWinConditions();
	}
}

void ACrisCyborgBoxingGameMode::StartMatch(ABoxer* InPlayer1, ABoxer* InPlayer2)
{
	Player1 = InPlayer1;
	Player2 = InPlayer2;
	CurrentRound = 1;
	RoundTimeRemaining = RoundDuration;
	SetGameState(EGameState::InMatch);

	if (Player1)
		Player1->ResetRound();
	if (Player2)
		Player2->ResetRound();
}

void ACrisCyborgBoxingGameMode::UpdateRoundTimer()
{
	RoundTimeRemaining -= GetWorldDeltaSeconds();

	if (RoundTimeRemaining <= 0.0f)
	{
		EndRound();
	}
}

void ACrisCyborgBoxingGameMode::CheckMatchWinConditions()
{
	if (!Player1 || !Player2)
		return;

	// KO Victory
	if (Player1->CurrentHealth <= 0.0f)
	{
		MatchWinner = Player2;
		EndMatch();
	}
	else if (Player2->CurrentHealth <= 0.0f)
	{
		MatchWinner = Player1;
		EndMatch();
	}
}

void ACrisCyborgBoxingGameMode::EndRound()
{
	SetGameState(EGameState::RoundEnd);

	if (CurrentRound < 3)
	{
		CurrentRound++;
		RoundTimeRemaining = RoundDuration;

		if (Player1)
			Player1->ResetRound();
		if (Player2)
			Player2->ResetRound();

		SetGameState(EGameState::InMatch);
	}
	else
	{
		// All 3 rounds completed
		MatchWinner = DetermineWinner();
		EndMatch();
	}
}

ABoxer* ACrisCyborgBoxingGameMode::DetermineWinner()
{
	if (!Player1 || !Player2)
		return nullptr;

	// Winner determined by score (punch count, combos, etc.)
	if (Player1->Score > Player2->Score)
		return Player1;
	else if (Player2->Score > Player1->Score)
		return Player2;

	// Tie - higher health wins
	if (Player1->CurrentHealth > Player2->CurrentHealth)
		return Player1;

	return Player2;
}

void ACrisCyborgBoxingGameMode::EndMatch()
{
	SetGameState(EGameState::MatchEnd);
}

void ACrisCyborgBoxingGameMode::SetGameState(EGameState NewState)
{
	CurrentGameState = NewState;
}
