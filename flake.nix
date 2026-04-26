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
              pkgs.installShellFiles
            ];

            installPhase = ''
              mkdir -p $out/bin
              cp mycli.sh $out/bin/mycli
              chmod +x $out/bin/mycli

              installShellCompletion --cmd mycli \
                --bash completions/mycli.bash \
                --zsh completions/_mycli \
                --fish completions/mycli.fish
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

      checks = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          pkg = self.packages.${system}.default;
        in {
          completion-files = pkgs.runCommand "check-completion-files" {
            inherit pkg;
          } ''
            echo "=== Package contents ==="
            find "$pkg" -type f | sort

            echo ""
            echo "Checking bash completion..."
            test -f "$pkg/share/bash-completion/completions/mycli"

            echo "Checking zsh completion..."
            test -f "$pkg/share/zsh/site-functions/_mycli"

            echo "Checking fish completion..."
            test -f "$pkg/share/fish/vendor_completions.d/mycli.fish"

            echo "All completion files present."
            touch $out
          '';
        }
      );
    };
}
