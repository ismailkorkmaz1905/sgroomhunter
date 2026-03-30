(function () {
  const payload = JSON.parse(document.getElementById("app-data").textContent);
  const currentLanguage = payload.lang;
  const currentPage = payload.page;
  const dictionary = payload.dictionaries[currentLanguage];
  const words = payload.words[currentLanguage];
  const typoEntries = payload.typos[currentLanguage];
  const app = document.getElementById("app");
  const availableLanguages = Object.keys(payload.dictionaries);

  const DAILY_EPOCH = Date.UTC(2026, 0, 1);
  const TYPO_QUESTIONS = 10;

  function getScopedKey(base, language) {
    return `${base}-${language}`;
  }

  function getSessionKey(base, language) {
    return `${base}-${language}-${getTodayKey()}`;
  }

  function normalizeWord(value) {
    return value.trim().toLocaleLowerCase(currentLanguage);
  }

  function displayWord(value) {
    return value.toLocaleUpperCase(currentLanguage);
  }

  function getTodayKey() {
    return new Date().toISOString().slice(0, 10);
  }

  function getDailyIndex(date, poolLength) {
    const dayIndex = Math.floor(
      (Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()) - DAILY_EPOCH) / 86400000,
    );
    return Math.abs(dayIndex) % poolLength;
  }

  function getDailyLadder(date, language) {
    return payload.ladders[language][getDailyIndex(date, payload.ladders[language].length)];
  }

  function getActiveLadder(language) {
    const pool = payload.ladders[language];
    const baseIndex = getDailyIndex(new Date(), pool.length);
    const bonusOffset = Number(sessionStorage.getItem(getSessionKey("word-game-daily-ladder-bonus", language)) || "0");
    const activeIndex = (baseIndex + bonusOffset) % pool.length;
    return {
      puzzle: pool[activeIndex],
      bonusOffset,
      activeIndex,
      hasNextBonus: pool.length > 0,
    };
  }

  function unlockNextBonus(language) {
    const key = getSessionKey("word-game-daily-ladder-bonus", language);
    const currentOffset = Number(sessionStorage.getItem(key) || "0");
    sessionStorage.setItem(key, String(currentOffset + 1));
  }

  function switchActiveLadder(language) {
    unlockNextBonus(language);
  }

  function shuffleWord(word) {
    if (word.length < 2) {
      return word;
    }

    const chars = word.split("");
    let shuffled = word;
    while (shuffled === word) {
      for (let index = chars.length - 1; index > 0; index -= 1) {
        const swapIndex = Math.floor(Math.random() * (index + 1));
        const current = chars[index];
        chars[index] = chars[swapIndex];
        chars[swapIndex] = current;
      }
      shuffled = chars.join("");
    }
    return shuffled;
  }

  function buildTypoOptions(entry) {
    const distractors = typoEntries
      .map((item) => item.correct)
      .filter((word) => word !== entry.correct)
      .sort(() => Math.random() - 0.5)
      .slice(0, 4);

    return [...distractors, entry.typo].sort(() => Math.random() - 0.5);
  }

  function countLetterChanges(left, right) {
    let changes = 0;
    for (let index = 0; index < left.length; index += 1) {
      if (left[index] !== right[index]) {
        changes += 1;
      }
    }
    return changes;
  }

  function getSavedLanguage() {
    return localStorage.getItem("word-game-language") || currentLanguage;
  }

  function saveLanguage(language) {
    localStorage.setItem("word-game-language", language);
  }

  function getProfileStorageKey() {
    return "word-game-player-profile";
  }

  function getPlayerProfile() {
    try {
      return JSON.parse(localStorage.getItem(getProfileStorageKey()) || "{}");
    } catch {
      return {};
    }
  }

  function getDisplayName() {
    const name = getPlayerProfile().displayName;
    return typeof name === "string" && name.trim() ? name.trim() : "";
  }

  function savePlayerProfile(profile) {
    localStorage.setItem(getProfileStorageKey(), JSON.stringify(profile));
  }

  function ensureClientId() {
    const profile = getPlayerProfile();
    if (profile.clientId) {
      return profile.clientId;
    }
    const clientId =
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : `client-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    savePlayerProfile({ ...profile, clientId });
    return clientId;
  }

  function formatGreeting(name) {
    return dictionary.profile.greeting.replace("{name}", name);
  }

  function getPlayerPrompt(name, context) {
    if (!name) {
      return "";
    }

    const prompts = {
      en: {
        daily: `${name}, you can take this one step by step.`,
        scramble: `Let's go, ${name}. Keep the pace light and fast.`,
        typo: `${name}, trust your eye and pick the odd one out.`,
        celebrate: `Nice work, ${name}.`,
        hint: `${name}, this clue should make the next step clearer.`,
      },
      tr: {
        daily: `Hadi ${name}, bunu adım adım çözebilirsin.`,
        scramble: `Hadi ${name}, ritmi koru ve hızlı git.`,
        typo: `${name}, gözüne güven ve farklı olanı seç.`,
        celebrate: `Tebrikler ${name}.`,
        hint: `${name}, bu ipucu sıradaki adımı biraz açacak.`,
      },
      nl: {
        daily: `${name}, rustig aan. Deze kun je stap voor stap oplossen.`,
        scramble: `Kom op, ${name}. Hou het tempo hoog.`,
        typo: `${name}, vertrouw op je oog en pak de vreemde eruit.`,
        celebrate: `Lekker bezig, ${name}.`,
        hint: `${name}, deze hint maakt de volgende trede hopelijk duidelijker.`,
      },
      id: {
        daily: `${name}, pelan saja. Ini bisa kamu pecahkan selangkah demi selangkah.`,
        scramble: `Ayo ${name}, jaga ritmenya dan tetap cepat.`,
        typo: `${name}, percaya sama matamu dan pilih yang paling janggal.`,
        celebrate: `Mantap, ${name}.`,
        hint: `${name}, hint ini semoga bikin langkah berikutnya lebih kebayang.`,
      },
      ms: {
        daily: `${name}, ambil selangkah demi selangkah. Yang ini boleh lepas.`,
        scramble: `Jom ${name}, kekalkan rentak dan terus laju.`,
        typo: `${name}, percaya mata anda dan pilih yang nampak janggal.`,
        celebrate: `Bagus, ${name}.`,
        hint: `${name}, petunjuk ini patut buat langkah seterusnya lebih jelas.`,
      },
    };

    const languagePrompts = prompts[currentLanguage] || prompts.en;
    return languagePrompts[context] || "";
  }

  function getLanguageFlag(language) {
    const flags = {
      en: "🇬🇧",
      tr: "🇹🇷",
      nl: "🇳🇱",
      id: "🇮🇩",
      ms: "🇲🇾",
    };
    return flags[language] || language.toUpperCase();
  }

  function submitProfileName(displayName) {
    const clientId = ensureClientId();
    return fetch("/profile-name", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        clientId,
        displayName,
        lang: currentLanguage,
      }),
    }).catch(function () {});
  }

  function pulseDevice(pattern) {
    if ("vibrate" in navigator) {
      navigator.vibrate(pattern);
    }
  }

  function saveLastPlayed(game) {
    const raw = localStorage.getItem("word-game-last-played");
    const state = raw ? JSON.parse(raw) : {};
    state[game] = getTodayKey();
    localStorage.setItem("word-game-last-played", JSON.stringify(state));
  }

  function updateMeta(page) {
    const seoMap = {
      home: ["homeTitle", "homeDescription"],
      "daily-ladder": ["dailyTitle", "dailyDescription"],
      "word-scramble": ["scrambleTitle", "scrambleDescription"],
      "typo-hunt": ["typoTitle", "typoDescription"],
      privacy: ["privacyTitle", "privacyDescription"],
      about: ["aboutTitle", "aboutDescription"],
      terms: ["termsTitle", "termsDescription"],
    };
    const [titleKey, descriptionKey] = seoMap[page];
    document.title = dictionary.seo[titleKey];
    document.documentElement.lang = currentLanguage;
    const meta = document.querySelector('meta[name="description"]');
    if (meta) {
      meta.setAttribute("content", dictionary.seo[descriptionKey]);
    }
  }

  function pathFor(language, page) {
    return page === "home" ? `/${language}` : `/${language}/${page}`;
  }

  function card(title, body, href, toneClass) {
    return `
      <article class="panel game-card ${toneClass}">
        <div class="card-kicker">${title}</div>
        <h2>${title}</h2>
        <p>${body}</p>
        <a class="cta-link" href="${href}">${dictionary.home.cta}</a>
      </article>
    `;
  }

  function layout(content, heroNote, options) {
    const config = options || {};
    const navItems = [
      ["home", dictionary.nav.home],
      ["daily-ladder", dictionary.nav.dailyWord],
      ["word-scramble", dictionary.nav.wordScramble],
      ["typo-hunt", dictionary.nav.typoHunt],
    ];

    return `
      <div class="shell">
        <header class="site-header">
          <div>
            <p class="eyebrow">${dictionary.home.eyebrow}</p>
            <a class="brand" href="${pathFor(currentLanguage, "home")}">${dictionary.brand}</a>
          </div>
          <div class="language-switcher" aria-label="${dictionary.common.language}">
            ${availableLanguages
              .map(function (language) {
                const active = currentLanguage === language ? "active" : "";
                return `<button type="button" data-lang="${language}" class="${active}" aria-label="${language.toUpperCase()}" title="${language.toUpperCase()}">${getLanguageFlag(language)}</button>`;
              })
              .join("")}
          </div>
        </header>
        <aside class="ad-placeholder top-banner">${dictionary.common.adLabel}: ${dictionary.common.topBanner}</aside>
        <div class="shell-body">
          <main class="main-content">
            ${config.leadContent || ""}
            <section class="panel hero-shell">
              <p class="eyebrow">${heroNote || dictionary.home.eyebrow}</p>
              <div class="welcome-strip" id="welcome-strip"></div>
              <div class="hero-shell-row">
                <div>
                  <h1>${dictionary.home.title}</h1>
                  <p>${dictionary.home.subtitle}</p>
                </div>
                <div class="hero-metrics">
                  <div class="metric-card"><span>${dictionary.home.metricsLanguages}</span><strong>${availableLanguages.length}</strong></div>
                  <div class="metric-card"><span>${dictionary.home.metricsGames}</span><strong>${dictionary.home.metricsGamesValue}</strong></div>
                  <div class="metric-card"><span>${dictionary.home.metricsSpeed}</span><strong>${dictionary.home.metricsSpeedValue}</strong></div>
                </div>
              </div>
            </section>
            <nav class="panel nav-tabs">
              ${navItems
                .map(function ([page, label]) {
                  const active = currentPage === page ? "active" : "";
                  return `<a class="${active}" href="${pathFor(currentLanguage, page)}">${label}</a>`;
                })
                .join("")}
            </nav>
            ${config.leadContent ? "" : content}
            ${config.leadContent ? `<div class="secondary-page-content">${content}</div>` : ""}
            <footer class="panel site-footer">
              <a href="${pathFor(currentLanguage, "privacy")}">${dictionary.common.privacy}</a>
              <a href="${pathFor(currentLanguage, "terms")}">${dictionary.common.terms}</a>
              <a href="${pathFor(currentLanguage, "about")}">${dictionary.common.about}</a>
            </footer>
          </main>
          <aside class="ad-placeholder sidebar-ad">${dictionary.common.adLabel}: ${dictionary.common.sidebar}</aside>
        </div>
      </div>
    `;
  }

  function renderHome() {
    app.innerHTML = layout(
      `
      <section class="game-grid">
        ${card(dictionary.nav.dailyWord, dictionary.home.dailyBody, pathFor(currentLanguage, "daily-ladder"), "card-ladder")}
        ${card(dictionary.nav.wordScramble, dictionary.home.scrambleBody, pathFor(currentLanguage, "word-scramble"), "card-scramble")}
        ${card(dictionary.nav.typoHunt, dictionary.home.typoBody, pathFor(currentLanguage, "typo-hunt"), "card-typo")}
      </section>
    `,
      dictionary.home.eyebrow,
    );
    bindLanguageSwitcher();
  }

  function renderDailyLadder() {
    const displayName = getDisplayName();
    const todayKey = getTodayKey();
    const ladderState = getActiveLadder(currentLanguage);
    const puzzle = ladderState.puzzle;
    const puzzleSignature = `${currentLanguage}:${puzzle.start}:${puzzle.target}:${puzzle.path.join("-")}`;
    const storageKey = getScopedKey("word-game-daily-ladder-state", currentLanguage);
    const streakKey = getScopedKey("word-game-daily-ladder-streak", currentLanguage);
    const maxMoves = puzzle.path.length - 1;
    const savedState = JSON.parse(localStorage.getItem(storageKey) || "null");
    const state =
      savedState && savedState.date === todayKey && savedState.puzzleSignature === puzzleSignature
        ? savedState
        : {
            date: todayKey,
            puzzleSignature,
            steps: [puzzle.start],
            completed: false,
            won: false,
            invalidAttemptCount: 0,
            flashMessage: "",
            feedbackTone: "",
            shakeTick: 0,
          };
    const streak = Number(localStorage.getItem(streakKey) || "0");
    const nextExpected = puzzle.path[state.steps.length];
    const hintVisible = !state.completed && state.invalidAttemptCount >= 2 && nextExpected;
    const revealVisible = !state.completed && state.invalidAttemptCount >= 3 && nextExpected;
    const hintText = hintVisible ? puzzle.clues[nextExpected] || displayWord(nextExpected) : "";
    const personalDailyPrompt = getPlayerPrompt(displayName, "daily");
    const personalCelebratePrompt = getPlayerPrompt(displayName, "celebrate");
    const personalHintPrompt = getPlayerPrompt(displayName, "hint");
    const progressWidth = `${Math.max(8, Math.round(((state.steps.length - 1) / maxMoves) * 100))}%`;
    const celebrationVisible = state.completed && state.won;

    localStorage.setItem(storageKey, JSON.stringify(state));

    const rows = Array.from({ length: maxMoves + 1 })
      .map(function (_, index) {
        const rung = state.steps[index] || (index === maxMoves ? puzzle.target : "");
        let rowClass = "ladder-rung";
        if (index === 0 || index === maxMoves) {
          rowClass += " locked";
        } else if (rung) {
          rowClass += " filled";
        }
        const label =
          index === 0
            ? dictionary.daily.start
            : index === maxMoves
              ? dictionary.daily.target
              : `${dictionary.daily.moves} ${index}`;
        return `
          <div class="${rowClass}">
            <span>${label}</span>
            <strong>${displayWord(rung)}</strong>
          </div>
        `;
      })
      .join("");

    const feedback = state.flashMessage || (state.completed
      ? state.won
        ? dictionary.daily.win
        : `${dictionary.daily.lose} ${puzzle.path.map(displayWord).join(" -> ")}`
      : dictionary.daily.rule);
    const celebrationMarkup = celebrationVisible
      ? `
        <section class="panel ladder-celebration">
          <p class="card-kicker">${ladderState.bonusOffset > 0 ? dictionary.daily.bonusLabel : dictionary.daily.title}</p>
          <h2>${personalCelebratePrompt ? `${personalCelebratePrompt} ${dictionary.daily.win}` : dictionary.daily.win}</h2>
          <p>${ladderState.hasNextBonus ? dictionary.daily.bonusBody : dictionary.daily.completed}</p>
          <div class="celebration-actions">
            ${
              ladderState.hasNextBonus
                ? `<button class="primary-button" type="button" id="bonus-ladder-button">${dictionary.daily.bonusCta}</button>`
                : `<a class="cta-link" href="${pathFor(currentLanguage, "home")}">${dictionary.common.backHome}</a>`
            }
          </div>
        </section>
      `
      : "";
    const switchButtonMarkup = payload.ladders[currentLanguage].length > 1
      ? `<button class="cta-link ghost-button" type="button" id="switch-ladder-button">${dictionary.daily.switchCta}</button>`
      : "";

    app.innerHTML = layout(
      `
      <section class="panel game-screen ladder-screen">
        <header class="section-header">
          <div>
              <h1>${dictionary.daily.title}</h1>
              <p>${dictionary.daily.body}</p>
              ${personalDailyPrompt ? `<p class="player-note">${personalDailyPrompt}</p>` : ""}
            </div>
          <div class="stats-row">
            <p class="stat-pill">${dictionary.daily.streak}: ${streak}</p>
            <p class="stat-pill">${dictionary.daily.moves}: ${state.steps.length - 1}/${maxMoves}</p>
            <p class="stat-pill">${dictionary.daily.bonusLabel}: ${ladderState.bonusOffset + 1}</p>
          </div>
        </header>
        ${switchButtonMarkup ? `<div class="ladder-switch-row">${switchButtonMarkup}</div>` : ""}
        <section class="panel ladder-meter">
          <div class="ladder-meter-labels">
            <span>${dictionary.daily.start}</span>
            <span>${dictionary.daily.target}</span>
          </div>
          <div class="ladder-meter-track">
            <div class="ladder-meter-fill" style="width: ${progressWidth}"></div>
          </div>
        </section>
        <section class="panel ladder-brief">
          <div><span>${dictionary.daily.start}</span><strong>${displayWord(puzzle.start)}</strong></div>
          <div><span>${dictionary.daily.target}</span><strong>${displayWord(puzzle.target)}</strong></div>
        </section>
        <div class="ladder-layout">
          <div class="ladder-board ${state.feedbackTone === "danger" ? "board-shake" : ""}" id="ladder-board">${rows}</div>
          <aside class="panel ladder-hint ${hintVisible ? "visible" : ""}">
            <p class="card-kicker">${dictionary.daily.hintTitle}</p>
            <h3>${dictionary.daily.hintBody}</h3>
            ${personalHintPrompt ? `<p class="player-note">${personalHintPrompt}</p>` : ""}
            <p>${hintText}</p>
            <span>${hintVisible ? dictionary.daily.retryHint : "&nbsp;"}</span>
            ${
              revealVisible
                ? `<button class="primary-button" type="button" id="reveal-ladder-button">${dictionary.daily.revealCta}</button>`
                : ""
            }
          </aside>
        </div>
        <form class="game-form" id="ladder-form">
          <label for="ladder-guess">${dictionary.daily.inputLabel}</label>
          <input id="ladder-guess" maxlength="${puzzle.start.length}" ${state.completed ? "disabled" : ""} />
          <button class="primary-button" type="submit" ${state.completed ? "disabled" : ""}>${dictionary.common.submit}</button>
        </form>
        <p class="feedback ${state.feedbackTone === "danger" ? "feedback-danger" : ""}" id="ladder-feedback">${feedback}</p>
        ${celebrationMarkup}
      </section>
    `,
      dictionary.home.dailyHero,
    );
    bindLanguageSwitcher();

    const form = document.getElementById("ladder-form");
    const input = document.getElementById("ladder-guess");
    const boardNode = document.getElementById("ladder-board");
    const bonusButton = document.getElementById("bonus-ladder-button");
    const revealButton = document.getElementById("reveal-ladder-button");
    const switchButton = document.getElementById("switch-ladder-button");

    if (!state.completed) {
      requestAnimationFrame(function () {
        input.focus();
      });
    }

    if (state.feedbackTone === "danger") {
      requestAnimationFrame(function () {
        boardNode.classList.remove("board-shake");
        void boardNode.offsetWidth;
        boardNode.classList.add("board-shake");
        input.focus();
        input.select();
      });
    }

    if (bonusButton) {
      bonusButton.addEventListener("click", function () {
        switchActiveLadder(currentLanguage);
        renderDailyLadder();
      });
    }

    if (switchButton) {
      switchButton.addEventListener("click", function () {
        switchActiveLadder(currentLanguage);
        renderDailyLadder();
      });
    }

    if (revealButton) {
      revealButton.addEventListener("click", function () {
        state.steps.push(nextExpected);
        state.completed = nextExpected === puzzle.target || state.steps.length - 1 >= maxMoves;
        state.won = nextExpected === puzzle.target;
        state.invalidAttemptCount = 0;
        state.flashMessage = dictionary.daily.revealDone;
        state.feedbackTone = "";
        state.puzzleSignature = puzzleSignature;
        localStorage.setItem(storageKey, JSON.stringify(state));
        pulseDevice([15, 35, 15]);
        renderDailyLadder();
      });
    }

    function commitInvalid(message, countTowardHint) {
      if (countTowardHint) {
        state.invalidAttemptCount += 1;
      }
      state.flashMessage =
        state.invalidAttemptCount >= 3 && nextExpected
          ? dictionary.daily.revealPrompt
          : state.invalidAttemptCount >= 2 && nextExpected
            ? dictionary.daily.revealHeadsUp
            : message;
      state.feedbackTone = "danger";
      state.shakeTick += 1;
      state.puzzleSignature = puzzleSignature;
      localStorage.setItem(storageKey, JSON.stringify(state));
      pulseDevice(state.invalidAttemptCount >= 2 && nextExpected ? [20, 40, 20] : [25]);
      renderDailyLadder();
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      const guess = normalizeWord(input.value);
      const previous = state.steps[state.steps.length - 1];

      if (guess.length !== puzzle.start.length) {
        commitInvalid(dictionary.daily.tooShort, false);
        return;
      }
      if (!puzzle.path.includes(guess)) {
        commitInvalid(dictionary.daily.invalidBounce, true);
        return;
      }
      if (countLetterChanges(previous, guess) !== 1) {
        commitInvalid(dictionary.daily.rule, true);
        return;
      }
      if (state.steps.includes(guess)) {
        commitInvalid(dictionary.daily.invalid, true);
        return;
      }

      state.steps.push(guess);
      state.won = guess === puzzle.target;
      state.completed = state.won || state.steps.length - 1 >= maxMoves;
      state.invalidAttemptCount = 0;
      state.flashMessage = "";
      state.feedbackTone = "";
      state.puzzleSignature = puzzleSignature;
      localStorage.setItem(storageKey, JSON.stringify(state));
      saveLastPlayed("daily-ladder");
      pulseDevice(state.won ? [18, 45, 18] : [12]);

      if (state.won) {
        localStorage.setItem(streakKey, String(streak + 1));
      }
      renderDailyLadder();
    });
  }

  function renderScramble() {
    const displayName = getDisplayName();
    const personalScramblePrompt = getPlayerPrompt(displayName, "scramble");
    const personalCelebratePrompt = getPlayerPrompt(displayName, "celebrate");
    const bestKey = getScopedKey("word-game-scramble-best", currentLanguage);
    let currentWord = words[Math.floor(Math.random() * words.length)];
    let currentScramble = shuffleWord(currentWord);
    let score = 0;
    let secondsLeft = 60;
    let intervalId = null;
    let currentGuess = "";
    let statusText = "";

    function pickNextWord() {
      const candidates = words.filter((word) => word !== currentWord);
      currentWord = candidates[Math.floor(Math.random() * candidates.length)];
      currentScramble = shuffleWord(currentWord);
    }

    function syncScrambleUI() {
      const timerNode = document.getElementById("scramble-timer");
      const scoreNode = document.getElementById("scramble-score");
      const wordNode = document.getElementById("scramble-word");
      const inputNode = document.getElementById("scramble-guess");
      const feedbackNode = document.getElementById("scramble-feedback");

      if (timerNode) {
        timerNode.textContent = `${dictionary.common.timeLeft}: ${secondsLeft}s`;
      }
      if (scoreNode) {
        scoreNode.textContent = `${dictionary.common.score}: ${score}`;
      }
      if (wordNode) {
        wordNode.textContent = displayWord(currentScramble);
      }
      if (inputNode && inputNode.value !== currentGuess) {
        inputNode.value = currentGuess;
      }
      if (feedbackNode) {
        feedbackNode.textContent = statusText || "\u00a0";
      }
    }

    function drawShell() {
      app.innerHTML = layout(
        `
        <section class="panel game-screen scramble-screen">
          <header class="section-header">
            <div>
              <h1>${dictionary.scramble.title}</h1>
              <p>${dictionary.scramble.body}</p>
              ${personalScramblePrompt ? `<p class="player-note">${personalScramblePrompt}</p>` : ""}
            </div>
            <div class="stats-row">
              <p class="stat-pill" id="scramble-timer">${dictionary.common.timeLeft}: ${secondsLeft}s</p>
              <p class="stat-pill" id="scramble-score">${dictionary.common.score}: ${score}</p>
            </div>
          </header>
          <p class="scramble-word" id="scramble-word">${displayWord(currentScramble)}</p>
          <form class="game-form" id="scramble-form">
            <label for="scramble-guess">${dictionary.scramble.inputLabel}</label>
            <input id="scramble-guess" placeholder="${dictionary.scramble.placeholder}" />
            <button class="primary-button" type="submit">${dictionary.common.submit}</button>
          </form>
          <p class="feedback" id="scramble-feedback">&nbsp;</p>
        </section>
      `,
        dictionary.home.scrambleHero,
      );
      bindLanguageSwitcher();
      requestAnimationFrame(function () {
        document.getElementById("scramble-guess").focus();
      });

      document.getElementById("scramble-form").addEventListener("submit", function (event) {
        event.preventDefault();
        const input = document.getElementById("scramble-guess");
        const guess = normalizeWord(input.value);
        if (guess === currentWord) {
          score += 1;
          const best = Math.max(Number(localStorage.getItem(bestKey) || "0"), score);
          localStorage.setItem(bestKey, String(best));
          saveLastPlayed("scramble");
          pulseDevice([12]);
          pickNextWord();
          currentGuess = "";
          statusText = dictionary.scramble.nextWord;
          syncScrambleUI();
          input.focus();
          return;
        }
        pulseDevice([25]);
        statusText = dictionary.common.wrong;
        syncScrambleUI();
      });

      document.getElementById("scramble-guess").addEventListener("input", function (event) {
        currentGuess = event.target.value;
      });
    }

    function renderEnd() {
      const best = Number(localStorage.getItem(bestKey) || "0");
      app.innerHTML = layout(
        `
        <section class="panel end-card">
          <h1>${personalCelebratePrompt ? `${personalCelebratePrompt} ${dictionary.scramble.gameOver}` : dictionary.scramble.gameOver}</h1>
          <p>${dictionary.common.score}: ${score} | ${dictionary.common.best}: ${best}</p>
          <aside class="ad-placeholder">${dictionary.common.adLabel}: ${dictionary.common.endScreen}</aside>
          <button class="primary-button" id="restart-scramble">${dictionary.common.playAgain}</button>
        </section>
      `,
        dictionary.home.scrambleHero,
      );
      bindLanguageSwitcher();
      document.getElementById("restart-scramble").addEventListener("click", renderScramble);
    }

    drawShell();
    intervalId = window.setInterval(function () {
      secondsLeft -= 1;
      if (secondsLeft <= 0) {
        clearInterval(intervalId);
        renderEnd();
        return;
      }
      syncScrambleUI();
    }, 1000);
  }

  function renderTypoHunt() {
    const displayName = getDisplayName();
    const personalTypoPrompt = getPlayerPrompt(displayName, "typo");
    const personalCelebratePrompt = getPlayerPrompt(displayName, "celebrate");
    const bestKey = getScopedKey("word-game-typo-best", currentLanguage);
    const totalQuestions = Math.min(TYPO_QUESTIONS, typoEntries.length);
    let questionIndex = 0;
    let score = 0;

    function draw() {
      const entry = typoEntries[questionIndex];
      const options = buildTypoOptions(entry);
      app.innerHTML = layout(
        `
        <section class="panel game-screen typo-screen">
          <header class="section-header">
            <div>
              <h1>${dictionary.typo.title}</h1>
              <p>${dictionary.typo.body}</p>
              ${personalTypoPrompt ? `<p class="player-note">${personalTypoPrompt}</p>` : ""}
            </div>
            <div class="stats-row">
              <p class="stat-pill">${dictionary.common.question}: ${questionIndex + 1}/${totalQuestions}</p>
              <p class="stat-pill">${dictionary.common.score}: ${score}</p>
            </div>
          </header>
          <p class="subtle">${dictionary.typo.instruction}</p>
          <div class="option-grid">
            ${options
              .map((option) => `<button class="option-button" type="button" data-option="${option}">${option}</button>`)
              .join("")}
          </div>
        </section>
      `,
        dictionary.home.typoHero,
      );
      bindLanguageSwitcher();

      app.querySelectorAll("[data-option]").forEach(function (button) {
        button.addEventListener(
          "click",
          function () {
            const selected = button.getAttribute("data-option");
            const buttons = Array.from(app.querySelectorAll("[data-option]"));
            buttons.forEach(function (item) {
              const isTarget = item.getAttribute("data-option") === entry.typo;
              if (isTarget) {
                item.classList.add("correct");
              }
              if (item === button && !isTarget) {
                item.classList.add("wrong");
              }
              item.disabled = true;
            });

            if (selected === entry.typo) {
              score += 1;
              const best = Math.max(Number(localStorage.getItem(bestKey) || "0"), score);
              localStorage.setItem(bestKey, String(best));
              pulseDevice([12]);
            } else {
              pulseDevice([25]);
            }
            saveLastPlayed("typo");

            const nextButton = document.createElement("button");
            nextButton.className = "next-button";
            nextButton.textContent = dictionary.typo.next;
            nextButton.addEventListener("click", function () {
              questionIndex += 1;
              if (questionIndex >= totalQuestions) {
                renderEnd();
                return;
              }
              draw();
            });
            app.querySelector(".game-screen").appendChild(nextButton);
          },
          { once: true },
        );
      });
    }

    function renderEnd() {
      const best = Number(localStorage.getItem(bestKey) || "0");
      app.innerHTML = layout(
        `
        <section class="panel end-card">
          <h1>${personalCelebratePrompt ? `${personalCelebratePrompt} ${dictionary.typo.gameOver}` : dictionary.typo.gameOver}</h1>
          <p>${dictionary.common.score}: ${score} | ${dictionary.common.best}: ${best}</p>
          <aside class="ad-placeholder">${dictionary.common.adLabel}: ${dictionary.common.endScreen}</aside>
          <button class="primary-button" id="restart-typo">${dictionary.common.playAgain}</button>
        </section>
      `,
        dictionary.home.typoHero,
      );
      bindLanguageSwitcher();
      document.getElementById("restart-typo").addEventListener("click", renderTypoHunt);
    }

    draw();
  }

  function renderPrivacy() {
    const pageContent = `
      <section class="panel game-screen privacy-screen">
        <header class="section-header">
          <div>
            <h1>${dictionary.privacy.title}</h1>
            <p>${dictionary.privacy.intro}</p>
          </div>
        </header>
        <ul class="privacy-list">
          <li>${dictionary.privacy.point1}</li>
          <li>${dictionary.privacy.point2}</li>
          <li>${dictionary.privacy.point3}</li>
          <li>${dictionary.privacy.point4}</li>
          <li>${dictionary.privacy.point5}</li>
          <li>${dictionary.privacy.point6}</li>
        </ul>
        <a class="cta-link" href="${pathFor(currentLanguage, "home")}">${dictionary.common.backHome}</a>
      </section>
    `;
    app.innerHTML = layout("", dictionary.common.privacy, { leadContent: pageContent });
    bindLanguageSwitcher();
  }

  function renderAbout() {
    const pageContent = `
      <section class="panel game-screen about-screen">
        <header class="section-header">
          <div>
            <h1>${dictionary.about.title}</h1>
            <p>${dictionary.about.intro}</p>
          </div>
        </header>
        <section class="panel about-card">
          <p class="card-kicker">${dictionary.about.contactLabel}</p>
          <p>${dictionary.about.contactBody}</p>
          <a class="cta-link" href="mailto:ismailkorkmaz490@gmail.com">${dictionary.about.emailLabel}: ismailkorkmaz490@gmail.com</a>
        </section>
        <a class="cta-link" href="${pathFor(currentLanguage, "home")}">${dictionary.common.backHome}</a>
      </section>
    `;
    app.innerHTML = layout("", dictionary.common.about, { leadContent: pageContent });
    bindLanguageSwitcher();
  }

  function renderTerms() {
    const pageContent = `
      <section class="panel game-screen terms-screen">
        <header class="section-header">
          <div>
            <h1>${dictionary.terms.title}</h1>
            <p>${dictionary.terms.intro}</p>
          </div>
        </header>
        <ul class="privacy-list">
          <li>${dictionary.terms.point1}</li>
          <li>${dictionary.terms.point2}</li>
          <li>${dictionary.terms.point3}</li>
          <li>${dictionary.terms.point4}</li>
          <li>${dictionary.terms.point5}</li>
        </ul>
        <a class="cta-link" href="${pathFor(currentLanguage, "home")}">${dictionary.common.backHome}</a>
      </section>
    `;
    app.innerHTML = layout("", dictionary.common.terms, { leadContent: pageContent });
    bindLanguageSwitcher();
  }

  function enhanceProfileUX() {
    const profile = getPlayerProfile();
    const welcomeStrip = document.getElementById("welcome-strip");
    if (welcomeStrip && profile.displayName) {
      welcomeStrip.innerHTML = `<p class="welcome-chip">${formatGreeting(profile.displayName)}</p>`;
    }

    if (profile.displayName || profile.dismissedNamePrompt) {
      return;
    }

    const overlay = document.createElement("div");
    overlay.className = "name-modal-overlay";
    overlay.innerHTML = `
      <div class="panel name-modal">
        <p class="card-kicker">${dictionary.common.about}</p>
        <h2>${dictionary.profile.promptTitle}</h2>
        <p>${dictionary.profile.promptBody}</p>
        <form id="name-form" class="game-form">
          <label for="display-name-input">${dictionary.profile.inputLabel}</label>
          <input id="display-name-input" maxlength="40" placeholder="${dictionary.profile.placeholder}" />
          <div class="name-modal-actions">
            <button class="primary-button" type="submit">${dictionary.profile.save}</button>
            <button class="cta-link ghost-button" type="button" id="skip-name-button">${dictionary.profile.skip}</button>
          </div>
        </form>
      </div>
    `;
    document.body.appendChild(overlay);

    const input = overlay.querySelector("#display-name-input");
    const form = overlay.querySelector("#name-form");
    const skipButton = overlay.querySelector("#skip-name-button");

    requestAnimationFrame(function () {
      input.focus();
    });

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      const displayName = input.value.trim().slice(0, 40);
      if (!displayName) {
        input.focus();
        return;
      }
      const nextProfile = { ...profile, clientId: ensureClientId(), displayName };
      savePlayerProfile(nextProfile);
      submitProfileName(displayName);
      overlay.remove();
      enhanceProfileUX();
    });

    skipButton.addEventListener("click", function () {
      savePlayerProfile({ ...profile, clientId: ensureClientId(), dismissedNamePrompt: true });
      overlay.remove();
    });
  }

  function bindLanguageSwitcher() {
    app.querySelectorAll("[data-lang]").forEach(function (button) {
      button.addEventListener("click", function () {
        const language = button.getAttribute("data-lang");
        saveLanguage(language);
        window.location.assign(pathFor(language, currentPage));
      });
    });
  }

  function boot() {
    const preferredLanguage = getSavedLanguage();
    if (preferredLanguage !== currentLanguage) {
      saveLanguage(currentLanguage);
    }

    updateMeta(currentPage);

    if (currentPage === "home") {
      renderHome();
    } else if (currentPage === "daily-ladder") {
      renderDailyLadder();
    } else if (currentPage === "word-scramble") {
      renderScramble();
    } else if (currentPage === "privacy") {
      renderPrivacy();
    } else if (currentPage === "about") {
      renderAbout();
    } else if (currentPage === "terms") {
      renderTerms();
    } else {
      renderTypoHunt();
    }

    enhanceProfileUX();
  }

  boot();
})();
