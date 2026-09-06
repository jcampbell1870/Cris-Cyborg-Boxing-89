#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "Boxer.h"
#include "CrisCyborgBoxingGameMode.generated.h"

UENUM(BlueprintType)
enum class EGameState : uint8
{
	MainMenu UMETA(DisplayName = "Main Menu"),
	Matchmaking UMETA(DisplayName = "Matchmaking"),
	InMatch UMETA(DisplayName = "In Match"),
	RoundEnd UMETA(DisplayName = "Round End"),
	MatchEnd UMETA(DisplayName = "Match End")
};

UCLASS()
class CRISCYBORGBOXING_API ACrisCyborgBoxingGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	ACrisCyborgBoxingGameMode();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaTime) override;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Match")
	ABoxer* Player1;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Match")
	ABoxer* Player2;

	UPROPERTY(BlueprintReadWrite, Category = "Match")
	EGameState CurrentGameState;

	UPROPERTY(BlueprintReadWrite, Category = "Match")
	int32 CurrentRound;

	UPROPERTY(BlueprintReadWrite, Category = "Match")
	float RoundTimeRemaining;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Match")
	float RoundDuration;

	UPROPERTY(BlueprintReadWrite, Category = "Match")
	ABoxer* MatchWinner;

	UFUNCTION(BlueprintCallable, Category = "Match")
	void StartMatch(ABoxer* InPlayer1, ABoxer* InPlayer2);

	UFUNCTION(BlueprintCallable, Category = "Match")
	void EndRound();

	UFUNCTION(BlueprintCallable, Category = "Match")
	void EndMatch();

	UFUNCTION(BlueprintCallable, Category = "State")
	void SetGameState(EGameState NewState);

	UFUNCTION(BlueprintCallable, Category = "Match")
	ABoxer* DetermineWinner();

protected:
	void UpdateRoundTimer();
	void CheckMatchWinConditions();
};
