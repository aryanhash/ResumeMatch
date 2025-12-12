# LaTeX Resume Generator Setup

The resume PDF generator uses LaTeX to create professional one-page resumes matching the [Jake's Resume template](https://www.overleaf.com/latex/templates/jakes-resume/syzfjbzwjncs).

## Requirements

The system requires `pdflatex` to be installed on the system. This is typically part of a LaTeX distribution:

### macOS
```bash
# Using Homebrew
brew install --cask mactex
# Or for a smaller installation
brew install --cask basictex
```

### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install texlive-latex-base texlive-fonts-recommended texlive-latex-extra
```

### Windows
Download and install [MiKTeX](https://miktex.org/download) or [TeX Live](https://www.tug.org/texlive/).

## Fallback Behavior

If LaTeX is not available, the system will automatically fall back to ReportLab-based PDF generation. However, the LaTeX version provides:
- ✅ Exact formatting matching Jake's Resume template
- ✅ Guaranteed one-page output
- ✅ Professional typography
- ✅ ATS-friendly formatting

## Required LaTeX Packages

The resume template requires the following LaTeX packages:
- `titlesec` - Section formatting
- `marvosym` - Symbols
- `enumitem` - List customization
- `hyperref` - Hyperlinks
- `fancyhdr` - Headers/footers
- `tabularx` - Advanced tables
- `geometry` - Page margins (auto-replaces deprecated `fullpage`)

### Installing Missing Packages

If you're using **BasicTeX** (minimal installation), you may need to install these packages manually:

```bash
# Update tlmgr first
sudo tlmgr update --self

# Install required packages
sudo tlmgr install titlesec marvosym enumitem hyperref fancyhdr tabularx geometry
```

**Note:** If you encounter missing package errors, the system will automatically fall back to ReportLab PDF generation. However, for best results (matching Jake's Resume template exactly), install the full TeX Live distribution:

```bash
# macOS - Full TeX Live (recommended)
brew install --cask mactex

# Or install all packages in BasicTeX
sudo tlmgr install scheme-full
```

## Testing LaTeX Installation

You can test if LaTeX is installed by running:
```bash
pdflatex --version
```

If this command works, LaTeX is properly installed.

To test if all required packages are available, try compiling a simple test:
```bash
echo '\documentclass{article}\usepackage{titlesec}\begin{document}Test\end{document}' > test.tex
pdflatex test.tex
rm test.tex test.aux test.log
```

## Docker Setup

If running in Docker, add LaTeX to your Dockerfile:

```dockerfile
# For Debian/Ubuntu based images
RUN apt-get update && \
    apt-get install -y texlive-latex-base texlive-fonts-recommended texlive-latex-extra && \
    rm -rf /var/lib/apt/lists/*
```
