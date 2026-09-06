#include "GameAPIClient.h"
#include "HttpModule.h"
#include "Interfaces/IHttpResponse.h"
#include "Json.h"
#include "JsonUtilities.h"

UGameAPIClient::UGameAPIClient()
	: ServerURL("http://localhost:5000"),
	  AuthToken(""),
	  CurrentPlayerId(0),
	  Http(nullptr)
{
}

void UGameAPIClient::Initialize(const FString& InServerURL)
{
	ServerURL = InServerURL;
	Http = &FHttpModule::Get();
}

void UGameAPIClient::GetAuthMessage()
{
	if (!Http.IsValid())
		return;

	FHttpRequestRef Request = Http->CreateRequest();
	Request->SetURL(ServerURL + "/api/auth/message");
	Request->SetVerb(TEXT("GET"));
	Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
	Request->OnProcessRequestComplete().BindUObject(this, &UGameAPIClient::OnAuthMessageResponse);
	Request->ProcessRequest();
}

void UGameAPIClient::Login(const FString& Address, const FString& Message, const FString& Signature)
{
	if (!Http.IsValid())
		return;

	FHttpRequestRef Request = Http->CreateRequest();
	Request->SetURL(ServerURL + "/api/auth/login");
	Request->SetVerb(TEXT("POST"));
	Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));

	// Create JSON payload
	TSharedPtr<FJsonObject> JsonPayload = MakeShareable(new FJsonObject());
	JsonPayload->SetStringField("address", Address);
	JsonPayload->SetStringField("message", Message);
	JsonPayload->SetStringField("signature", Signature);

	FString JsonStr;
	TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&JsonStr);
	FJsonSerializer::Serialize(JsonPayload.ToSharedRef(), Writer);

	Request->SetContentAsString(JsonStr);
	Request->OnProcessRequestComplete().BindUObject(this, &UGameAPIClient::OnLoginResponse);
	Request->ProcessRequest();
}

void UGameAPIClient::FindMatch(int32 PlayerId)
{
	if (!Http.IsValid())
		return;

	FHttpRequestRef Request = Http->CreateRequest();
	Request->SetURL(ServerURL + "/api/matches/findmatch");
	Request->SetVerb(TEXT("POST"));
	Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
	Request->SetHeader(TEXT("Authorization"), TEXT("Bearer ") + AuthToken);

	TSharedPtr<FJsonObject> JsonPayload = MakeShareable(new FJsonObject());
	JsonPayload->SetNumberField("playerId", PlayerId);

	FString JsonStr;
	TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&JsonStr);
	FJsonSerializer::Serialize(JsonPayload.ToSharedRef(), Writer);

	Request->SetContentAsString(JsonStr);
	Request->OnProcessRequestComplete().BindUObject(this, &UGameAPIClient::OnMatchFoundResponse);
	Request->ProcessRequest();
}

void UGameAPIClient::ClaimReward(int32 PlayerId, float Amount, const FString& RewardType)
{
	if (!Http.IsValid())
		return;

	FHttpRequestRef Request = Http->CreateRequest();
	Request->SetURL(ServerURL + "/api/rewards/claim");
	Request->SetVerb(TEXT("POST"));
	Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
	Request->SetHeader(TEXT("Authorization"), TEXT("Bearer ") + AuthToken);

	TSharedPtr<FJsonObject> JsonPayload = MakeShareable(new FJsonObject());
	JsonPayload->SetNumberField("playerId", PlayerId);
	JsonPayload->SetNumberField("amount", Amount);
	JsonPayload->SetStringField("rewardType", RewardType);

	FString JsonStr;
	TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&JsonStr);
	FJsonSerializer::Serialize(JsonPayload.ToSharedRef(), Writer);

	Request->SetContentAsString(JsonStr);
	Request->OnProcessRequestComplete().BindUObject(this, &UGameAPIClient::OnRewardClaimedResponse);
	Request->ProcessRequest();
}

void UGameAPIClient::OnAuthMessageResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful)
{
	if (bWasSuccessful && Response.IsValid())
	{
		UE_LOG(LogTemp, Warning, TEXT("Auth Message: %s"), *Response->GetContentAsString());
	}
}

void UGameAPIClient::OnLoginResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful)
{
	if (!bWasSuccessful || !Response.IsValid())
	{
		OnLoginFailed.Broadcast(TEXT("Network error"));
		return;
	}

	TSharedPtr<FJsonObject> JsonObject = MakeShareable(new FJsonObject());
	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Response->GetContentAsString());
	FJsonSerializer::Deserialize(Reader, JsonObject);

	if (JsonObject->GetBoolField("success"))
	{
		AuthToken = JsonObject->GetStringField("token");
		FString PlayerName = JsonObject->GetObjectField("player")->GetStringField("username");
		CurrentPlayerId = JsonObject->GetObjectField("player")->GetNumberField("id");
		OnLoginSuccess.Broadcast(AuthToken, PlayerName);
	}
	else
	{
		OnLoginFailed.Broadcast(JsonObject->GetStringField("error"));
	}
}

void UGameAPIClient::OnMatchFoundResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful)
{
	if (!bWasSuccessful || !Response.IsValid())
	{
		UE_LOG(LogTemp, Error, TEXT("Match search failed"));
		return;
	}

	TSharedPtr<FJsonObject> JsonObject = MakeShareable(new FJsonObject());
	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Response->GetContentAsString());
	FJsonSerializer::Deserialize(Reader, JsonObject);

	int32 MatchId = JsonObject->GetNumberField("matchId");
	OnMatchFound.Broadcast(MatchId);
}

void UGameAPIClient::OnRewardClaimedResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful)
{
	if (!bWasSuccessful || !Response.IsValid())
	{
		UE_LOG(LogTemp, Error, TEXT("Reward claim failed"));
		return;
	}

	TSharedPtr<FJsonObject> JsonObject = MakeShareable(new FJsonObject());
	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Response->GetContentAsString());
	FJsonSerializer::Deserialize(Reader, JsonObject);

	float Amount = JsonObject->GetNumberField("amount");
	OnRewardClaimed.Broadcast(Amount);
}
