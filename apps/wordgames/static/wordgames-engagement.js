(function () {
  const HISTORY_KEY = "word-game-history-v2";

  function safeParse(value, fallback) {
    try {
      return JSON.parse(value);
    } catch {
      return fallback;
    }
  }

  function getHistory() {
    return safeParse(localStorage.getItem(HISTORY_KEY), []);
  }

  function saveHistory(entries) {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(entries.slice(0, 80)));
  }

  function recordSession(entry) {
    const normalized = {
      ...entry,
      playedAt: entry.playedAt || new Date().toISOString(),
    };
    const history = getHistory();
    history.unshift(normalized);
    saveHistory(history);
    return normalized;
  }

  function getHistoryForLanguage(language) {
    return getHistory().filter(function (entry) {
      return entry.lang === language;
    });
  }

  function getHistorySummary(language) {
    const entries = getHistoryForLanguage(language);
    const byGame = {};
    entries.forEach(function (entry) {
      if (!byGame[entry.game]) {
        byGame[entry.game] = {
          sessions: 0,
          bestScore: 0,
          lastPlayedAt: "",
          wins: 0,
        };
      }
      const current = byGame[entry.game];
      current.sessions += 1;
      current.bestScore = Math.max(current.bestScore, Number(entry.score || 0));
      current.lastPlayedAt = current.lastPlayedAt || entry.playedAt;
      current.wins += entry.outcome === "win" ? 1 : 0;
    });

    return {
      totalSessions: entries.length,
      recent: entries.slice(0, 18),
      byGame,
    };
  }

  function buildShareText(dictionary, entry) {
    const title = dictionary.brand;
    const labels = {
      "daily-ladder": dictionary.nav.dailyWord,
      "word-scramble": dictionary.nav.wordScramble,
      "typo-hunt": dictionary.nav.typoHunt,
      "word-chain": dictionary.nav.wordChain,
      "category-blitz": dictionary.nav.categoryBlitz,
      "mini-crossword": dictionary.nav.miniCrossword,
    };
    const gameLabel = labels[entry.game] || entry.game;

    if (entry.game === "daily-ladder") {
      return `${gameLabel}: ${entry.start} -> ${entry.target} | ${dictionary.daily.moves}: ${entry.moves} | ${dictionary.common.score}: ${entry.score || 0}`;
    }
    if (typeof entry.score === "number") {
      return `${gameLabel}: ${dictionary.common.score} ${entry.score}`;
    }
    return `${gameLabel}: ${entry.outcome || "played"}`;
  }

  async function shareResult(dictionary, entry) {
    const text = buildShareText(dictionary, entry);
    const title = dictionary.brand;
    if (navigator.share) {
      try {
        await navigator.share({ title, text });
        return "shared";
      } catch {
        return "dismissed";
      }
    }

    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      return "copied";
    }

    return "unsupported";
  }

  window.WordSprintEngagement = {
    getHistorySummary,
    recordSession,
    shareResult,
  };
})();
