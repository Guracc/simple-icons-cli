class SimpleIcons < Formula
  include Language::Python::Virtualenv

  desc "CLI for Simple Icons with icon format conversion"
  homepage "https://github.com/Guracc/simple-icons-cli"
  url "https://github.com/Guracc/simple-icons-cli/archive/refs/tags/v0.2.2.tar.gz"
  sha256 "17df9069973a8f04ae3784511fe1643974cb58566b37e49b900eebfc072cfd5b"
  license "MIT"

  depends_on "cairo"
  depends_on "python@3.12"
  depends_on "uv" => :build

  def install
    venv = virtualenv_create(libexec, "python3.12")
    system "uv", "pip", "install", "--python", venv.python_executable, "."
    bin.install_symlink libexec/"bin/simple-icons"
  end

  test do
    system "#{bin}/simple-icons", "--help"
  end
end
