## [2.3.1](https://github.com/AnthusAI/SQLBot/compare/v2.3.0...v2.3.1) (2025-12-02)


### Bug Fixes

* update tests to use text mode as default ([3986263](https://github.com/AnthusAI/SQLBot/commit/3986263fcf64cd1035426b07cbe670398ac221ce))

# [2.3.0](https://github.com/AnthusAI/SQLBot/compare/v2.2.4...v2.3.0) (2025-12-02)


### Features

* make text-based UI the default, add --textual flag for TUI ([76c9182](https://github.com/AnthusAI/SQLBot/commit/76c91829d18b4b5f6e856c968d78195207bbe092))

## [2.2.4](https://github.com/AnthusAI/SQLBot/compare/v2.2.3...v2.2.4) (2025-12-02)


### Bug Fixes

* auto-submit queries ending with semicolon in text mode ([9b067a3](https://github.com/AnthusAI/SQLBot/commit/9b067a3b2e890f6cbe6a75fe4186214c046b72c9))

## [2.2.3](https://github.com/AnthusAI/SQLBot/compare/v2.2.2...v2.2.3) (2025-12-02)


### Bug Fixes

* improve multi-line input UX - now requires blank line to submit after first line ([e9382ce](https://github.com/AnthusAI/SQLBot/commit/e9382ce0e7721edeab1e24e020eb8f52cc18a051))

## [2.2.2](https://github.com/AnthusAI/SQLBot/compare/v2.2.1...v2.2.2) (2025-12-01)


### Bug Fixes

* include chat history in messages list for agent invocation ([135ad89](https://github.com/AnthusAI/SQLBot/commit/135ad899fe748c041b8989249ed442c8c1e936c0))

## [2.2.1](https://github.com/AnthusAI/SQLBot/compare/v2.2.0...v2.2.1) (2025-12-01)


### Bug Fixes

* pass callbacks via config parameter in agent.invoke ([e9807c6](https://github.com/AnthusAI/SQLBot/commit/e9807c638562ef0c95950dc844b5f8f643e99f2a))

# [2.2.0](https://github.com/AnthusAI/SQLBot/compare/v2.1.0...v2.2.0) (2025-12-01)


### Features

* update to langchain 1.1.0 API ([f8ed99c](https://github.com/AnthusAI/SQLBot/commit/f8ed99c25572f9a34d58e0655ca66123f0000e2f))

# [2.1.0](https://github.com/AnthusAI/SQLBot/compare/v2.0.0...v2.1.0) (2025-12-01)


### Features

* add debug logging, conversation persistence, and performance indicators ([5080619](https://github.com/AnthusAI/SQLBot/commit/50806193739b6ea63020815a8680ab7c3007ff89))

# [2.0.0](https://github.com/AnthusAI/SQLBot/compare/v1.3.1...v2.0.0) (2025-10-09)


### Features

* add multi-line input support for text and textual modes ([2439e8b](https://github.com/AnthusAI/SQLBot/commit/2439e8b6d6a26df9ad34cfa97c3f26a8e0d4e48e))


### BREAKING CHANGES

* none

## [1.3.1](https://github.com/AnthusAI/SQLBot/compare/v1.3.0...v1.3.1) (2025-10-07)


### Bug Fixes

* ensure OPENAI_API_KEY loads from .env in current directory ([9b199c0](https://github.com/AnthusAI/SQLBot/commit/9b199c0281f0baa006a4d3be4bf43035fa675493))

# [1.3.0](https://github.com/AnthusAI/SQLBot/compare/v1.2.1...v1.3.0) (2025-09-23)


### Features

* **export:** add data export functionality for query results ([91367a5](https://github.com/AnthusAI/SQLBot/commit/91367a5f92f067c3e64c56dbc8aa82aaebf92c40))

## [1.2.2](https://github.com/AnthusAI/SQLBot/compare/v1.2.1...v1.2.2) (2025-09-21)


### Bug Fixes

* improve dbt setup error reporting with detailed diagnostics and actionable guidance
* add missing dbt-sqlite adapter support for SQLite database connections
* enhance error parsing to provide specific installation commands for missing adapters

## [1.2.1](https://github.com/AnthusAI/SQLBot/compare/v1.2.0...v1.2.1) (2025-09-21)


### Bug Fixes

* correct dbt profile discovery error messages and configuration ([b29395b](https://github.com/AnthusAI/SQLBot/commit/b29395b2854c6beed906f6e0283da066c39f2f41))

# [1.2.0](https://github.com/AnthusAI/SQLBot/compare/v1.1.0...v1.2.0) (2025-09-14)


### Features

* enhance Sakila database setup and CLI functionality ([b947606](https://github.com/AnthusAI/SQLBot/commit/b9476063dc7b19913c9a93796921baaa7dd97a87))

# [1.1.0](https://github.com/AnthusAI/SQLBot/compare/v1.0.3...v1.1.0) (2025-09-14)


### Features

* YAML config file with dotconfig. ([b10042a](https://github.com/AnthusAI/SQLBot/commit/b10042a3d7973766eb55e9578db0fb05da03d3cb))

## [1.0.3](https://github.com/AnthusAI/SQLBot/compare/v1.0.2...v1.0.3) (2025-09-13)


### Bug Fixes

* update test assertions for SQLBot rebranding ([9bbb3ec](https://github.com/AnthusAI/SQLBot/commit/9bbb3ecf5490ee53e6e8d9bf4f19000d86a879fb))

## [1.0.2](https://github.com/AnthusAI/SQLBot/compare/v1.0.1...v1.0.2) (2025-09-13)


### Bug Fixes

* test PyPI automation with credentials ([41b7508](https://github.com/AnthusAI/SQLBot/commit/41b750877dd664fddadcea77955b0fd8e822d810))

## [1.0.1](https://github.com/AnthusAI/SQLBot/compare/v1.0.0...v1.0.1) (2025-09-13)


### Bug Fixes

* update repository URL to SQLBot ([a588dba](https://github.com/AnthusAI/SQLBot/commit/a588dbaaa421bdf7848579797101c4224ddd2cba))

# 1.0.0 (2025-09-13)


### Bug Fixes

* add package-lock.json for semantic-release ([d9ae517](https://github.com/AnthusAI/SQLBot/commit/d9ae517f19e3cdab4d158e0872e205b09f2d0df8))


* 🎉 Rebrand SQLBot to SQLBot v0.2.0 - Finally pushing to PyPI! ([0490ad7](https://github.com/AnthusAI/SQLBot/commit/0490ad7ba388d163f33443a2ac41e182778316f2))


### Features

* add semantic-release automation ([7b6f855](https://github.com/AnthusAI/SQLBot/commit/7b6f855b1505abeb40e93e9144267c997e97c945))


### BREAKING CHANGES

* CLI command is now 'sqlbot' instead of 'qbot'

Ready for the world! 🚀
