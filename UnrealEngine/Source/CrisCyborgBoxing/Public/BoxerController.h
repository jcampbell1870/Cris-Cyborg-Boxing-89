#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "InputActionValue.h"
#include "BoxerController.generated.h"

class ABoxer;

UCLASS()
class CRISCYBORGBOXING_API ABoxerController : public APawn
{
	GENERATED_BODY()

public:
	ABoxerController();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaTime) override;
	virtual void SetupPlayerInputComponent(class UInputComponent* PlayerInputComponent) override;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Boxer")
	ABoxer* ControlledBoxer;

	UFUNCTION()
	void OnPunchLeft();

	UFUNCTION()
	void OnPunchRight();

	UFUNCTION()
	void OnSpecial();

	UFUNCTION()
	void OnDodge();

	UFUNCTION()
	void OnMoveForward(float Value);

	UFUNCTION()
	void OnMoveRight(float Value);

	UFUNCTION(BlueprintCallable, Category = "Input")
	void SetBoxerInput(ABoxer* InBoxer);

private:
	FVector2D MoveInput;
};
