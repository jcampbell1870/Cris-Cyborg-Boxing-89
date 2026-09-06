# Windows Store (MSIX) packaging assets

`Package.appxmanifest` references these image files, which must be added
here before packaging (they are binary image assets and are not included in
source control by this scaffold):

| File                     | Size (px) | Purpose                                |
|--------------------------|-----------|------------------------------------------|
| `StoreLogo.png`          | 50x50     | Store listing logo                      |
| `Square44x44Logo.png`    | 44x44     | Taskbar / app list icon                 |
| `Square150x150Logo.png`  | 150x150   | Start menu medium tile                  |
| `Wide310x150Logo.png`    | 310x150   | Start menu wide tile                    |
| `SplashScreen.png`       | 620x300   | Splash screen shown while the app loads |

Export these from the game's branding/logo source art (for example the
Unreal Engine project's icon assets) at the exact sizes above. The Microsoft
Store submission portal (Partner Center) will validate these dimensions and
reject the package if they don't match.
