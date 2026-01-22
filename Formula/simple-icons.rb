class SimpleIcons < Formula
  include Language::Python::Virtualenv

  desc "CLI for Simple Icons with icon format conversion"
  homepage "https://github.com/Guracc/simple-icons-cli"
  url "https://github.com/Guracc/simple-icons-cli/archive/refs/tags/v0.2.0.tar.gz"
  sha256 "ee87548490c8c307d9a7943c11fc1e224c63c0958092eaf704a77c6dc3f412d6"
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
