# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- [@HiromuHota][HiromuHota]: Fix a bug that an html file is not created at a given path.
  ([#64](https://github.com/HazyResearch/pdftotree/pull/64))
- [@HiromuHota][HiromuHota]: Switch the output format from "HTML-like" to hOCR.
  ([#62](https://github.com/HazyResearch/pdftotree/pull/62))
- [@HiromuHota][HiromuHota]: Greedily extract contents from PDF even if it looks scanned.
  ([#71](https://github.com/HazyResearch/pdftotree/pull/71))

## 0.4.1 - 2020-09-21

### Fixed
- [@lukehsiao][lh]: Temporarily add `chardet` to requirements until
  [pdfminer/pdfminer.six#213](https://github.com/pdfminer/pdfminer.six/issues/213) is fixed.
  ([#47](https://github.com/HazyResearch/pdftotree/issues/47))
- [@mgoo][mgoo]: Fix ValueError when a Node instance is a single element.
  ([#49](https://github.com/HazyResearch/pdftotree/pull/49))

[lh]: https://github.com/lukehsiao
[mgoo]: https://github.com/mgoo
[HiromuHota]: https://github.com/HiromuHota