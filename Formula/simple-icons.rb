class SimpleIcons < Formula
  include Language::Python::Virtualenv

  desc "CLI for Simple Icons with icon format conversion"
  homepage "https://github.com/Guracc/simple-icons-cli"
  url "https://github.com/Guracc/simple-icons-cli/archive/refs/tags/v0.2.2.tar.gz"
  sha256 "17df9069973a8f04ae3784511fe1643974cb58566b37e49b900eebfc072cfd5b"
  license "MIT"

  depends_on "cairo"
  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    system "#{bin}/simple-icons", "--help"
  end
end
