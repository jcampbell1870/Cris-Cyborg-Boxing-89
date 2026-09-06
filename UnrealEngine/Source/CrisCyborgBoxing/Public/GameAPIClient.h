#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "Http.h"
#include "JsonUtilities.h"
#include "GameAPIClient.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FOnLoginSuccess, const FString&, Token, const FString&, PlayerName);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_One(FOnLoginFailed, const FString&, ErrorMessage);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_One(FOnMatchFound, int32, MatchId);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_One(FOnRewardClaimed, float, Amount);

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
};
