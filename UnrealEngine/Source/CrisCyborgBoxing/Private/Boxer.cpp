#include "Boxer.h"

ABoxer::ABoxer()
{
	PrimaryActorTick.TickInterval = 0.016f;

	MaxHealth = 100.0f;
	CurrentHealth = MaxHealth;
	Speed = 5;
	Power = 5;
	Defense = 5;
	Stamina = 100;
	Score = 0;
	bIsKnockedDown = false;
	KnockdownTimer = 0.0f;
	Difficulty = EBoxerDifficulty::Medium;

	// Disable default rotation
	bUseControllerRotationPitch = false;
	bUseControllerRotationYaw = false;
	bUseControllerRotationRoll = false;
}

void ABoxer::BeginPlay()
{
	Super::BeginPlay();
	CurrentHealth = MaxHealth;
}

void ABoxer::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	// Handle knockdown timer
	if (bIsKnockedDown)
	{
		KnockdownTimer -= DeltaTime;
		if (KnockdownTimer <= 0.0f)
		{
			bIsKnockedDown = false;
		}
	}
}

void ABoxer::TakeDamage(float DamageAmount)
{
	CurrentHealth -= DamageAmount;
	if (CurrentHealth <= 0.0f)
	{
		CurrentHealth = 0.0f;
		bIsKnockedDown = true;
		KnockdownTimer = 3.0f; // 3 second knockout
	}
	else if (CurrentHealth < MaxHealth * 0.3f)
	{
		// Knockdown if health < 30%
		bIsKnockedDown = true;
		KnockdownTimer = 1.0f;
	}
}

void ABoxer::Punch(bool bIsLeftPunch)
{
	if (bIsKnockedDown)
		return;

	// Damage calculation: Power stat + random variance
	float BaseDamage = 5.0f + (Power * 2);
	float Damage = BaseDamage + FMath::RandRange(-2.0f, 2.0f);

	Score += 10;
}

void ABoxer::Special()
{
	if (bIsKnockedDown)
		return;

	// Special move: 1.5x damage
	float SpecialDamage = (5.0f + (Power * 2)) * 1.5f;
	Score += 25;
}

void ABoxer::Dodge()
{
	if (bIsKnockedDown)
		return;

	// Reduce damage taken by Defense stat
	// Implementation handled in receiving boxer
}

bool ABoxer::IsKnockedDown() const
{
	return bIsKnockedDown;
}

void ABoxer::ResetRound()
{
	CurrentHealth = MaxHealth;
	bIsKnockedDown = false;
	KnockdownTimer = 0.0f;
}
