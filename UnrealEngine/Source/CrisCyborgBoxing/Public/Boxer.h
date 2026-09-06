#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "InputActionValue.h"
#include "Boxer.generated.h"

UENUM(BlueprintType)
enum class EBoxerDifficulty : uint8
{
	Easy UMETA(DisplayName = "Easy"),
	Medium UMETA(DisplayName = "Medium"),
	Hard UMETA(DisplayName = "Hard"),
	Expert UMETA(DisplayName = "Expert")
};

UCLASS()
class CRISCYBORGBOXING_API ABoxer : public ACharacter
{
	GENERATED_BODY()

public:
	ABoxer();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaTime) override;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Boxer Stats")
	FString BoxerName;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Boxer Stats")
	float MaxHealth;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Boxer Stats")
	float CurrentHealth;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Boxer Stats")
	int32 Speed;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Boxer Stats")
	int32 Power;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Boxer Stats")
	int32 Defense;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Boxer Stats")
	int32 Stamina;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Boxer Stats")
	EBoxerDifficulty Difficulty;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Boxer Stats")
	int32 Score;

	UFUNCTION(BlueprintCallable, Category = "Combat")
	void TakeDamage(float DamageAmount);

	UFUNCTION(BlueprintCallable, Category = "Combat")
	void Punch(bool bIsLeftPunch);

	UFUNCTION(BlueprintCallable, Category = "Combat")
	void Special();

	UFUNCTION(BlueprintCallable, Category = "Combat")
	void Dodge();

	UFUNCTION(BlueprintCallable, Category = "Combat")
	bool IsKnockedDown() const;

	UFUNCTION(BlueprintCallable, Category = "State")
	void ResetRound();

protected:
	bool bIsKnockedDown;
	float KnockdownTimer;
};
