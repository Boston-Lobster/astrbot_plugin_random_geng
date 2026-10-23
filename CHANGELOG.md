# Changelog

## 1.5.1

- Fix leaderboard requests returning business code 500 by explicitly sending the empty `tags` parameter for the unfiltered top-five list.
- Use the current official API host `https://api.hguofichp.cn` for random and leaderboard requests.
- Add regression coverage for the API request contract and business-level failures.

## 1.5.0

- Read plain text from AstrBot's message text fields instead of treating the message component chain as a string.
- Resolve the selected LLM provider by its exact configured provider ID.
- Restore HTTPS certificate verification and check HTTP status before parsing API responses.
- Handle both list and object forms of leaderboard data safely.
- Require the AI judge response to be exactly `YES` after trimming whitespace.
- Add offline unit tests using AstrBot framework stubs.

## 1.4.0

- Make automatic AI judging strict by default and allow the cooldown to be configured.
