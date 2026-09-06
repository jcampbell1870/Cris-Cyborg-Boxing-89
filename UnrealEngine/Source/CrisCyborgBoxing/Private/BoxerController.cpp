#include "BoxerController.h"
#include "Boxer.h"
#include "InputActionValue.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"

ABoxerController::ABoxerController()
{
	PrimaryActorTick.TickInterval = 0.016f;
	ControlledBoxer = nullptr;
	MoveInput = FVector2D::ZeroVector;
}

void ABoxerController::BeginPlay()
{
	Super::BeginPlay();
}

void ABoxerController::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
}

void ABoxerController::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);

	if (PlayerInputComponent)
	{
		PlayerInputComponent->BindAction("PunchLeft", IE_Pressed, this, &ABoxerController::OnPunchLeft);
		PlayerInputComponent->BindAction("PunchRight", IE_Pressed, this, &ABoxerController::OnPunchRight);
		PlayerInputComponent->BindAction("Special", IE_Pressed, this, &ABoxerController::OnSpecial);
		PlayerInputComponent->BindAction("Dodge", IE_Pressed, this, &ABoxerController::OnDodge);

		PlayerInputComponent->BindAxis("MoveForward", this, &ABoxerController::OnMoveForward);
		PlayerInputComponent->BindAxis("MoveRight", this, &ABoxerController::OnMoveRight);
	}
}

void ABoxerController::OnPunchLeft()
{
	if (ControlledBoxer && !ControlledBoxer->IsKnockedDown())
	{
		ControlledBoxer->Punch(true);
	}
}

void ABoxerController::OnPunchRight()
{
	if (ControlledBoxer && !ControlledBoxer->IsKnockedDown())
	{
		ControlledBoxer->Punch(false);
	}
}

void ABoxerController::OnSpecial()
{
	if (ControlledBoxer && !ControlledBoxer->IsKnockedDown())
	{
		ControlledBoxer->Special();
	}
}

void ABoxerController::OnDodge()
{
	if (ControlledBoxer && !ControlledBoxer->IsKnockedDown())
	{
		ControlledBoxer->Dodge();
	}
}

void ABoxerController::OnMoveForward(float Value)
{
	MoveInput.Y = Value;
}

void ABoxerController::OnMoveRight(float Value)
{
	MoveInput.X = Value;
}

void ABoxerController::SetBoxerInput(ABoxer* InBoxer)
{
	ControlledBoxer = InBoxer;
}
