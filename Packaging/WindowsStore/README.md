# Windows Store (MSIX) packaging

Cris Cyborg Boxing is a Win64 (Windows 10/11, 64-bit) Unreal Engine game.
This folder contains the scaffolding needed to package a built copy of the
game as an MSIX package for submission to the Microsoft Store, alongside the
free downloadable ZIP published from the [GitHub Pages site](../../docs).

## 1. Build the game for Win64

From a Windows machine with Unreal Engine 5.3 installed:

```powershell
"C:\Program Files\Epic Games\UE_5.3\Engine\Build\BatchFiles\RunUAT.bat" BuildCookRun ^
  -project="<repo>\UnrealEngine\CrisCyborgBoxing.uproject" ^
  -noP4 -platform=Win64 -clientconfig=Shipping -cook -allmaps -build -stage -pak -archive ^
  -archivedirectory="<repo>\Packaging\Output"
```

This produces a packaged build under
`Packaging\Output\Windows\CrisCyborgBoxing\Binaries\Win64\`, containing
`CrisCyborgBoxing.exe`.

## 2. Reserve the app name and get store identity values

1. Create/sign in to a [Microsoft Partner Center](https://partner.microsoft.com/dashboard)
   developer account.
2. Reserve the app name "Cris Cyborg Boxing" under **Apps and games > New product**.
3. Under **App identity**, copy the generated **Package/Identity/Name** and
   **Publisher ID** values.
4. Update [`Package.appxmanifest`](Package.appxmanifest) `Identity/@Name` and
   `Identity/@Publisher` with those values (and `PublisherDisplayName`).

## 3. Add the required image assets

See [`Assets/README.md`](Assets/README.md) for the exact files and sizes the
manifest expects (store logo, tile logos, splash screen).

## 4. Build the MSIX package

Install the Windows 10/11 SDK (provides `makeappx.exe` and `signtool.exe`),
then run:

```powershell
Packaging\WindowsStore\Build-MsixPackage.ps1 `
  -BuildDirectory "Packaging\Output\Windows\CrisCyborgBoxing\Binaries\Win64" `
  -OutputPackage "Packaging\Output\CrisCyborgBoxing.msix"
```

Add `-CertificatePath` with a `.pfx` code-signing certificate if you want to
sideload and test the package locally before submitting it - the Store
re-signs submitted packages itself, so this isn't required for submission.

## 5. Submit to the Microsoft Store

1. In Partner Center, open the reserved app listing and go to **Packages**.
2. Upload the generated `.msix` file.
3. Fill in store listing details (screenshots, description, age ratings).
   Disclose the Arcade1870 (ARC) reward system and MetaMask wallet
   integration in the listing and age-rating questionnaire, since it
   involves optional blockchain/cryptocurrency interaction.
4. Submit for certification.

## Notes on ARC rewards in a Store build

The Store build uses the exact same backend API and
`Arcade1870RewardVault` contract as the free downloadable build and the
Unreal Engine `GameAPIClient` - no code changes are required between the two
distributions. Players still connect their own wallet and pay their own gas
to claim ARC; the app and Microsoft Store never hold player funds.
