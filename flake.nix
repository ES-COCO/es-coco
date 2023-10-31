{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };
  outputs = {nixpkgs, ...}: let
    inherit (nixpkgs) lib;
    withSystem = f:
      lib.fold lib.recursiveUpdate {}
      (map f ["x86_64-linux" "x86_64-darwin" "aarch64-linux" "aarch64-darwin"]);
  in
    withSystem (
      system: let
        pkgs = nixpkgs.legacyPackages.${system};
        inherit (pkgs) stdenv lib mkShell;
        apple_deps = with pkgs.darwin.apple_sdk_11_0.frameworks; [Accelerate CoreGraphics CoreML CoreVideo];
      in {
        devShells.${system}.default = mkShell {
          packages = with pkgs;
            [
              python310
              poetry
              ffmpeg
              openai-whisper-cpp
            ]
            ++ lib.optionals stdenv.isDarwin apple_deps;

          nativeBuildInputs = with pkgs; [
            pkg-config
          ];

          LD_LIBRARY_PATH = lib.makeLibraryPath [
            stdenv.cc.cc
          ];

          CFLAGS = "-stdlib=libc++";

          # Put the venv on the repo, so direnv can access it
          POETRY_VIRTUALENVS_IN_PROJECT = "true";
          POETRY_VIRTUALENVS_PATH = "{project-dir}/.venv";

          # Use python from path, so you can use a different version to the one bundled with poetry
          POETRY_VIRTUALENVS_PREFER_ACTIVE_PYTHON = "true";

          # Use ipdb
          PYTHONBREAKPOINT = "ipdb.set_trace";
        };
      }
    );
}
