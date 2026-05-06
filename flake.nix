{
  description = "Flake for inspire_hand_ws with unitree_sdk2_python";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11"; # ou une version plus récente si besoin
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            # Dépendances Python de base
            python312
            python312Packages.pip
            python312Packages.setuptools
            python312Packages.wheel
            python312Packages.numpy
            python312Packages.opencv4
            python312Packages.cyclonedds-python

            # Intégration directe de unitree_sdk2_python
            (python312.pkgs.buildPythonPackage rec {
              pname = "unitree-sdk2-python";
              version = "0-unstable-2025-03-05";
              src = pkgs.fetchFromGitHub {
                owner = "unitreerobotics";
                repo = "unitree_sdk2_python";
                rev = "986f39d54182badc1aa3a0c282bcd898fba4ef20";
                sha256 = "sha256-0n5v9B92Sr2MnGSH91ucXHZWOAzypER0hNZAAspLVvM=";
              };
              pyproject = true;
              buildInputs = [
                python312Packages.setuptools
                python312Packages.wheel                
                python312Packages.cyclonedds-python
                python312Packages.opencv4
                python312Packages.numpy
              ];
              pythonRelaxDeps = [ python312Packages.cyclonedds-python ];
              pythonImportsCheck = [ "unitree_sdk2py" ];
              meta = {
                description = "Python interface for Unitree SDK2";
                homepage = "https://github.com/unitreerobotics/unitree_sdk2_python";
                license = pkgs.lib.licenses.bsd3;
              };
            })
          ];
        };
      }
    );
}
