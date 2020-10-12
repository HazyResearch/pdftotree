# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- [@HiromuHota][HiromuHota]: Support for Python 3.8.
  ([#86](https://github.com/HazyResearch/pdftotree/pull/86))

### Changed
- [@HiromuHota][HiromuHota]: Switch the output format from "HTML-like" to hOCR.
  ([#62](https://github.com/HazyResearch/pdftotree/pull/62))
- [@HiromuHota][HiromuHota]: Loosen Keras' version restriction, which is now unnecessarily strict.
  ([#68](https://github.com/HazyResearch/pdftotree/pull/68))
- [@HiromuHota][HiromuHota]: Greedily extract contents from PDF even if it looks scanned.
  ([#71](https://github.com/HazyResearch/pdftotree/pull/71))
- [@HiromuHota][HiromuHota]: Upgrade Keras to 2.4.0 or later (and TensorFlow 2.2 or later).
  ([#86](https://github.com/HazyResearch/pdftotree/pull/86))

### Removed
- [@HiromuHota][HiromuHota]: Remove "favor_figures" option and extract everything.
  ([#77](https://github.com/HazyResearch/pdftotree/pull/77))
- [@HiromuHota][HiromuHota]: Remove "dry_run" option.
  ([#89](https://github.com/HazyResearch/pdftotree/pull/89))

### Fixed
- [@HiromuHota][HiromuHota]: Fix a bug that an html file is not created at a given path.
  ([#64](https://github.com/HazyResearch/pdftotree/pull/64))
- [@HiromuHota][HiromuHota]: Extract LTChar even if they are not children of LTTextLine.
  ([#79](https://github.com/HazyResearch/pdftotree/pull/79))

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