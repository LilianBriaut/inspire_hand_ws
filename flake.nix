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
            pymodbus,
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
              pymodbus
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
