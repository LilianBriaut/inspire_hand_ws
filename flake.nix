{
  description = "Flake for inspire_hand_ws with unitree_sdk2_python";

  inputs = {
    gepetto.url = "github:gepetto/nix/pull/311/merge";
  };

  outputs =
    inputs:
    inputs.gepetto.lib.mkFlakoboros inputs (
      { ... }:
      {
        pyPackages.pymodbus_369 =
          {
            pymodbus,
            fetchFromGitHub,
          }:
          pymodbus.overrideAttrs (
            drv-final: drv-prev: {
              version = "3.6.9";
              src = fetchFromGitHub {
                inherit (drv-prev.src) owner repo;
                tag = "v${drv-final.version}";
                hash = "sha256-ScqxDO0hif8p3C6+vvm7FgSEQjCXBwUPOc7Y/3OfkoI=";
              };
              disabledTestPaths = [ ];
            }
          );
        pyPackages.inspire-hand-ws =
          {
            lib,
            buildPythonPackage,
            setuptools,
            cyclonedds-python_10,
            numpy,
            pyqt5,
            pyqtgraph,
            qt5,
            colorcet,
            pymodbus_369,
            pyserial,
            unitree-sdk2-python,
          }:
          buildPythonPackage (_finalAttrs: {
            name = "inspire-hand-sdk";
            version = "0-unstable-2026-05-07";
            pyproject = true;
            src = lib.cleanSource ./inspire_hand_sdk;
            build-system = [ setuptools ];
            dependencies = [
              cyclonedds-python_10
              numpy
              pyqt5
              pyqtgraph
              colorcet
              pymodbus_369
              pyserial
              unitree-sdk2-python
            ];
            pythonRelaxDeps = [ "pymodbus" ];
            pythonImportsCheck = [ "inspire_sdkpy" ];
            passthru.qt-env = lib.makeSearchPathOutput "bin" qt5.qtbase.qtPluginPrefix [
              qt5.qtbase
              qt5.qtdeclarative
              qt5.qtwayland
            ];
          });
      }
    );
}
