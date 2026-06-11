{
  description = "Flake for inspire_hand_ws with unitree_sdk2_python";

  inputs = {
    gepetto.url = "github:gepetto/nix";
  };

  outputs =
    inputs:
    inputs.gepetto.lib.mkFlakoboros inputs (
      { lib, ... }:
      {
        pyOverrideAttrs.inspire-hand-sdk =
          { pkgs-final, ... }:
          {
            src = lib.cleanSource ./inspire_hand_sdk;

            env.QT_PLUGIN_PATH = lib.makeSearchPathOutput "bin" pkgs-final.qt5.qtbase.qtPluginPrefix [
              pkgs-final.qt5.qtbase
              pkgs-final.qt5.qtdeclarative
              pkgs-final.qt5.qtwayland
            ];
          };
      }
    );
}
