{
  description = "CLI tool with PTY completion tests";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in {
      packages = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          # Bundle python with the pexpect library for the PTY test
          pythonEnv = pkgs.python3.withPackages (ps: [ ps.pexpect ]);
        in {
          default = pkgs.stdenv.mkDerivation {
            pname = "mycli";
            version = "1.0.0";

            src = ./.;

            # We explicitly need bashInteractive because standard stdenv bash 
            # drops interactive capabilities in the sandbox.
            nativeBuildInputs = [
              pythonEnv
              pkgs.bashInteractive
              pkgs.zsh
              pkgs.fish
            ];

            installPhase = ''
              mkdir -p $out/bin
              cp mycli.sh $out/bin/mycli
              chmod +x $out/bin/mycli

              # Standard paths for completions
              mkdir -p $out/share/bash-completion/completions
              cp completions/mycli.bash $out/share/bash-completion/completions/mycli

              mkdir -p $out/share/zsh/site-functions
              cp completions/_mycli $out/share/zsh/site-functions/_mycli

              mkdir -p $out/share/fish/vendor_completions.d
              cp completions/mycli.fish $out/share/fish/vendor_completions.d/mycli.fish
            '';

            doCheck = true;
            checkPhase = ''
              echo "Running PTY shell completion tests..."
              
              # Zsh and Fish require a writable HOME directory to initialize interactively
              export HOME=$(mktemp -d)
              
              # Run the test suite
              python3 test_completions.py
            '';
          };
        }
      );
    };
}
