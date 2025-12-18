{
  description = "Python 3.13";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
  }:
    flake-utils.lib.eachDefaultSystem (
      system: let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };
      in {
        devShells.default = pkgs.mkShell {
          name = "python-base-env";

          buildInputs = [
            pkgs.python313
            pkgs.python313Packages.pip
            pkgs.python313Packages.virtualenv
          ];
        };
      }
    );
}
