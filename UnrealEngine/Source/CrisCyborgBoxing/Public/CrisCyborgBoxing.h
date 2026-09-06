#pragma once

#include "Modules/ModuleManager.h"

class FCrisCyborgBoxingModule : public IModuleInterface
{
public:
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;
};
