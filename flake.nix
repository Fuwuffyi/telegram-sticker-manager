{
  description = "Python 3.13 telegram sticker organizer";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };

        python = pkgs.python313;
        pythonPackages = python.pkgs;
      in
      {
        devShells.default = pkgs.mkShell {
          name = "python-telegram-gatherer-env";

          buildInputs = with pkgs; [
            python
            pythonPackages.pip
            pythonPackages.virtualenv
            sqlite
          ];
        };
      }
    );
}
