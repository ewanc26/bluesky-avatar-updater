# flake.nix — Nix dev shell for bluesky-avatar-updater.
#
# Provides Python 3 tooling (the original prototype was a Python script) for
# any remaining scripting or testing alongside the Rust binary.

{
  description = "bluesky-avatar-updater — hourly avatar/banner updater for Bluesky";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in {
      devShells = forAllSystems (system:
        let pkgs = nixpkgs.legacyPackages.${system}; in
        {
          # Python-heavy dev shell: the Rust build toolchain is expected to come
          # from the user's environment (rustup) rather than nixpkgs.
          default = pkgs.mkShell {
            packages = with pkgs; [
              python3
              python3Packages.pip
              python3Packages.virtualenv
              python3Packages.requests
              python3Packages.python-dotenv
            ];

            shellHook = ''
              echo "bluesky-avatar-updater dev shell ready (Python 3)"
            '';
          };
        }
      );

      # Code formatting via nixfmt
      formatter = forAllSystems (pkgs: pkgs.nixfmt-rfc-style);
    };
}
