#include "CrisCyborgBoxing.h"

#define LOCTEXT_NAMESPACE "FCrisCyborgBoxingModule"

void FCrisCyborgBoxingModule::StartupModule()
{
	UE_LOG(LogTemp, Warning, TEXT("CrisCyborg Boxing Module Loaded"));
}

void FCrisCyborgBoxingModule::ShutdownModule()
{
	UE_LOG(LogTemp, Warning, TEXT("CrisCyborg Boxing Module Unloaded"));
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FCrisCyborgBoxingModule, CrisCyborgBoxing)
