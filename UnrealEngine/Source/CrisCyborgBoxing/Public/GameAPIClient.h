#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "Http.h"
#include "JsonUtilities.h"
#include "GameAPIClient.generated.h"

USTRUCT(BlueprintType)
struct FArcadeRewardClaim
{
	GENERATED_BODY()

	// Database id of the issued reward record (not the on-chain nonce).
	UPROPERTY(BlueprintReadOnly, Category = "Rewards")
	int32 RewardId = 0;

	// Amount of Arcade1870 (ARC) authorized by this claim.
	UPROPERTY(BlueprintReadOnly, Category = "Rewards")
	float Amount = 0.f;

	// EIP-712 claim(recipient,amount,nonce,deadline) parameters and signature.
	// These are passed as decimal strings since ARC amounts/nonces/deadlines
	// are uint256 values that may exceed the range of a 32-bit/64-bit number.
	UPROPERTY(BlueprintReadOnly, Category = "Rewards")
	FString Nonce;

	UPROPERTY(BlueprintReadOnly, Category = "Rewards")
	FString Deadline;

	UPROPERTY(BlueprintReadOnly, Category = "Rewards")
	FString Signature;

	// Arcade1870 (ARC) token contract address.
	UPROPERTY(BlueprintReadOnly, Category = "Rewards")
	FString TokenAddress;

	// Shared Arcade1870RewardVault address (same vault used by Crypto Chess).
	UPROPERTY(BlueprintReadOnly, Category = "Rewards")
	FString RewardVaultAddress;

	UPROPERTY(BlueprintReadOnly, Category = "Rewards")
	int32 ChainId = 1;

	UPROPERTY(BlueprintReadOnly, Category = "Rewards")
	FString ChainName;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FOnLoginSuccess, const FString&, Token, const FString&, PlayerName);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_One(FOnLoginFailed, const FString&, ErrorMessage);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_One(FOnMatchFound, int32, MatchId);

// Broadcast once the backend has issued a signed Arcade1870RewardVault claim.
// This does NOT mean the player has received ARC yet: the game (or a
// connected wallet) must still submit claim(Amount, Nonce, Deadline,
// Signature) to RewardVaultAddress on ChainId to actually receive the
// tokens, the same non-custodial flow used by Crypto Chess.
DECLARE_DYNAMIC_MULTICAST_DELEGATE_One(FOnRewardClaimed, const FArcadeRewardClaim&, Claim);

UCLASS()
class CRISCYBORGBOXING_API UGameAPIClient : public UObject
{
	GENERATED_BODY()

public:
	UGameAPIClient();

	UFUNCTION(BlueprintCallable, Category = "API")
	void Initialize(const FString& InServerURL);

	UFUNCTION(BlueprintCallable, Category = "API")
	void GetAuthMessage();

	UFUNCTION(BlueprintCallable, Category = "API")
	void Login(const FString& Address, const FString& Message, const FString& Signature);

	UFUNCTION(BlueprintCallable, Category = "API")
	void FindMatch(int32 PlayerId);

	UFUNCTION(BlueprintCallable, Category = "API")
	void ClaimReward(int32 PlayerId, float Amount, const FString& RewardType);

	// Call after the player's wallet has successfully submitted the vault
	// claim transaction on-chain, so the backend can record the tx hash.
	UFUNCTION(BlueprintCallable, Category = "API")
	void CompleteReward(int32 RewardId, const FString& TransactionHash);

	UPROPERTY(BlueprintAssignable, Category = "Events")
	FOnLoginSuccess OnLoginSuccess;

	UPROPERTY(BlueprintAssignable, Category = "Events")
	FOnLoginFailed OnLoginFailed;

	UPROPERTY(BlueprintAssignable, Category = "Events")
	FOnMatchFound OnMatchFound;

	UPROPERTY(BlueprintAssignable, Category = "Events")
	FOnRewardClaimed OnRewardClaimed;

	FString AuthToken;
	int32 CurrentPlayerId;

private:
	FString ServerURL;
	TSharedPtr<IHttpModule> Http;

	void OnAuthMessageResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful);
	void OnLoginResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful);
	void OnMatchFoundResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful);
	void OnRewardClaimedResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful);
	void OnRewardCompletedResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful);
};
