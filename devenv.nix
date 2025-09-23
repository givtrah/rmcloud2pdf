{ pkgs, lib, config, inputs, ... }:


let 
  buildInputs = with pkgs; [
    stdenv.cc.cc
    libuv
    zlib
    glibc
		freetype
  ];

in

{
  env.GREET = "devenv";

  packages = [ pkgs.git pkgs.dbus pkgs.pkg-config pkgs.glibc pkgs.glib pkgs.freetype];

  # https://devenv.sh/languages/
  # languages.rust.enable = true;

  # https://devenv.sh/processes/
  # processes.cargo-watch.exec = "cargo-watch";

  # https://devenv.sh/services/
  # services.postgres.enable = true;

  # https://devenv.sh/scripts/

  languages.python = {
    enable = true;
    uv  = {
      enable = true;
      sync.enable = true;
      sync.allExtras = true;
    };
    venv = {
      enable = true;
    };

  };

}
