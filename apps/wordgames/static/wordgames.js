(function () {
  const payload = JSON.parse(document.getElementById("app-data").textContent);
  const currentLanguage = payload.lang;
  const currentPage = payload.page;
  const dictionary = payload.dictionaries[currentLanguage];
  const words = payload.words[currentLanguage];
  const typoEntries = payload.typos[currentLanguage];
  const chainWords = payload.chains[currentLanguage];
  const categoryRounds = payload.categories[currentLanguage];
  const crosswordPuzzles = payload.crosswords[currentLanguage];
  const app = document.getElementById("app");
  const availableLanguages = Object.keys(payload.dictionaries);
  const brandMarkUrl = "/static/brand/wordsprint-mark.svg";

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

  function getActiveCrossword(language) {
    const pool = payload.crosswords[language];
    const baseIndex = getDailyIndex(new Date(), pool.length);
    const offset = Number(sessionStorage.getItem(getSessionKey("word-game-crossword-offset", language)) || "0");
    const activeIndex = (baseIndex + offset) % pool.length;
    return {
      puzzle: pool[activeIndex],
      activeIndex,
      hasNext: pool.length > 1,
    };
  }

  function switchActiveCrossword(language) {
    const key = getSessionKey("word-game-crossword-offset", language);
    const currentOffset = Number(sessionStorage.getItem(key) || "0");
    sessionStorage.setItem(key, String(currentOffset + 1));
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

  function buildCrosswordPuzzle(puzzle) {
    const size = puzzle.size;
    const cells = Array.from({ length: size * size }, function () {
      return {
        blocked: false,
        solution: "",
        number: "",
      };
    });
    const numberingMap = {};
    let nextNumber = 1;

    (puzzle.blocks || []).forEach(function ([row, col]) {
      const index = row * size + col;
      cells[index].blocked = true;
    });

    function ensureNumberForStart(row, col) {
      const key = `${row}-${col}`;
      if (!numberingMap[key]) {
        numberingMap[key] = String(nextNumber);
        nextNumber += 1;
      }
      return numberingMap[key];
    }

    puzzle.entries.forEach(function (entry) {
      const letters = Array.from(normalizeWord(entry.answer));
      letters.forEach(function (letter, offset) {
        const row = entry.row + (entry.direction === "down" ? offset : 0);
        const col = entry.col + (entry.direction === "across" ? offset : 0);
        const index = row * size + col;
        cells[index].solution = letter;
      });

      const startIndex = entry.row * size + entry.col;
      const entryNumber = ensureNumberForStart(entry.row, entry.col);
      cells[startIndex].number = entryNumber;
    });

    return {
      size,
      cells,
      totalFillable: cells.filter(function (cell) {
        return !cell.blocked;
      }).length,
      entries: puzzle.entries.map(function (entry) {
        return {
          ...entry,
          number: ensureNumberForStart(entry.row, entry.col),
          answer: normalizeWord(entry.answer),
        };
      }),
    };
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
      en: {
        label: "English",
        markup: '<svg class="flag-icon" viewBox="0 0 60 40" aria-hidden="true"><rect width="60" height="40" rx="6" fill="#012169"/><path d="M0 0l60 40M60 0L0 40" stroke="#FFF" stroke-width="8"/><path d="M0 0l60 40M60 0L0 40" stroke="#C8102E" stroke-width="4"/><path d="M30 0v40M0 20h60" stroke="#FFF" stroke-width="14"/><path d="M30 0v40M0 20h60" stroke="#C8102E" stroke-width="8"/></svg>',
      },
      tr: {
        label: "Türkçe",
        markup: '<svg class="flag-icon" viewBox="0 0 60 40" aria-hidden="true"><rect width="60" height="40" rx="6" fill="#E30A17"/><circle cx="24" cy="20" r="10" fill="#FFF"/><circle cx="27" cy="20" r="8" fill="#E30A17"/><polygon points="35,20 43,17 43,23" fill="#FFF"/></svg>',
      },
      nl: {
        label: "Nederlands",
        markup: '<svg class="flag-icon" viewBox="0 0 60 40" aria-hidden="true"><rect width="60" height="40" rx="6" fill="#21468B"/><rect width="60" height="26.67" rx="6" fill="#FFF"/><path d="M0 0h60v13.33H0z" fill="#AE1C28"/></svg>',
      },
      id: {
        label: "Bahasa Indonesia",
        markup: '<svg class="flag-icon" viewBox="0 0 60 40" aria-hidden="true"><rect width="60" height="40" rx="6" fill="#FFF"/><path d="M0 0h60v20H0z" fill="#CE1126"/></svg>',
      },
      ms: {
        label: "Bahasa Melayu",
        markup: '<svg class="flag-icon" viewBox="0 0 60 40" aria-hidden="true"><rect width="60" height="40" rx="6" fill="#FFF"/><g fill="#CC0001"><rect y="0" width="60" height="4"/><rect y="8" width="60" height="4"/><rect y="16" width="60" height="4"/><rect y="24" width="60" height="4"/><rect y="32" width="60" height="4"/></g><rect width="28" height="22" rx="6" fill="#010066"/><circle cx="12" cy="11" r="6" fill="#FFCC00"/><circle cx="14" cy="11" r="5" fill="#010066"/><polygon points="20,11 22.8,12 21,9.5 23.8,8.5 20.5,8.4 20,5.3 19,8.3 15.9,7.3 18.2,9.7 16.1,12 19.2,11.7 19.8,14.8" fill="#FFCC00"/></svg>',
      },
    };
    return flags[language] || null;
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
        "word-chain": ["chainTitle", "chainDescription"],
        "category-blitz": ["categoryTitle", "categoryDescription"],
        "mini-crossword": ["crosswordTitle", "crosswordDescription"],
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
        ["word-chain", dictionary.nav.wordChain],
        ["category-blitz", dictionary.nav.categoryBlitz],
        ["mini-crossword", dictionary.nav.miniCrossword],
      ];

    return `
      <div class="shell">
        <header class="site-header">
          <div>
            <p class="eyebrow">${dictionary.home.eyebrow}</p>
            <a class="brand" href="${pathFor(currentLanguage, "home")}" aria-label="${dictionary.brand}">
              <img class="brand-mark" src="${brandMarkUrl}" alt="" />
              <span class="brand-wordmark">${dictionary.brand}</span>
            </a>
          </div>
          <div class="language-switcher" aria-label="${dictionary.common.language}">
            ${availableLanguages
              .map(function (language) {
                const active = currentLanguage === language ? "active" : "";
                const flag = getLanguageFlag(language);
                const content = flag
                  ? flag.markup
                  : language.toUpperCase();
                return `<button type="button" data-lang="${language}" class="${active}" aria-label="${flag ? flag.label : language.toUpperCase()}" title="${flag ? flag.label : language.toUpperCase()}">${content}</button>`;
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
        ${card(dictionary.nav.wordChain, dictionary.home.chainBody, pathFor(currentLanguage, "word-chain"), "card-chain")}
        ${card(dictionary.nav.categoryBlitz, dictionary.home.categoryBody, pathFor(currentLanguage, "category-blitz"), "card-category")}
        ${card(dictionary.nav.miniCrossword, dictionary.home.crosswordBody, pathFor(currentLanguage, "mini-crossword"), "card-crossword")}
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

  function renderWordChain() {
    const displayName = getDisplayName();
    const personalChainPrompt = getPlayerPrompt(displayName, "daily");
    const personalCelebratePrompt = getPlayerPrompt(displayName, "celebrate");
    const bestKey = getScopedKey("word-game-chain-best", currentLanguage);
    const pool = chainWords.slice();
    let currentWord = pool[Math.floor(Math.random() * pool.length)];
    let score = 0;
    let secondsLeft = 45;
    let intervalId = null;
    let currentGuess = "";
    let statusText = dictionary.chain.rule;
    const usedWords = new Set([currentWord]);

    function syncChainUI() {
      const timerNode = document.getElementById("chain-timer");
      const scoreNode = document.getElementById("chain-score");
      const wordNode = document.getElementById("chain-word");
      const inputNode = document.getElementById("chain-guess");
      const feedbackNode = document.getElementById("chain-feedback");

      if (timerNode) {
        timerNode.textContent = `${dictionary.common.timeLeft}: ${secondsLeft}s`;
      }
      if (scoreNode) {
        scoreNode.textContent = `${dictionary.common.score}: ${score}`;
      }
      if (wordNode) {
        wordNode.textContent = displayWord(currentWord);
      }
      if (inputNode && inputNode.value !== currentGuess) {
        inputNode.value = currentGuess;
      }
      if (feedbackNode) {
        feedbackNode.textContent = statusText || "\u00a0";
      }
    }

    function drawShell() {
      const currentLastLetter = displayWord(currentWord.slice(-1));
      app.innerHTML = layout(
        `
        <section class="panel game-screen chain-screen">
          <header class="section-header">
            <div>
              <h1>${dictionary.chain.title}</h1>
              <p>${dictionary.chain.body}</p>
              ${personalChainPrompt ? `<p class="player-note">${personalChainPrompt}</p>` : ""}
            </div>
            <div class="stats-row">
              <p class="stat-pill" id="chain-timer">${dictionary.common.timeLeft}: ${secondsLeft}s</p>
              <p class="stat-pill" id="chain-score">${dictionary.common.score}: ${score}</p>
            </div>
          </header>
          <section class="panel chain-brief">
            <div><span>${dictionary.daily.target}</span><strong id="chain-word">${displayWord(currentWord)}</strong></div>
            <div><span>${dictionary.chain.rule}</span><strong>${currentLastLetter}</strong></div>
          </section>
          <form class="game-form" id="chain-form">
            <label for="chain-guess">${dictionary.chain.inputLabel}</label>
            <input id="chain-guess" placeholder="${dictionary.chain.placeholder}" />
            <button class="primary-button" type="submit">${dictionary.common.submit}</button>
          </form>
          <p class="feedback" id="chain-feedback">${statusText}</p>
        </section>
      `,
        dictionary.home.chainHero,
      );
      bindLanguageSwitcher();
      requestAnimationFrame(function () {
        document.getElementById("chain-guess").focus();
      });

      document.getElementById("chain-form").addEventListener("submit", function (event) {
        event.preventDefault();
        const input = document.getElementById("chain-guess");
        const guess = normalizeWord(input.value);
        const requiredStart = normalizeWord(currentWord.slice(-1));

        if (!guess) {
          statusText = dictionary.chain.rule;
          syncChainUI();
          return;
        }
        if (guess[0] !== requiredStart) {
          pulseDevice([25]);
          statusText = dictionary.chain.wrongStart;
          syncChainUI();
          return;
        }
        if (!pool.includes(guess)) {
          pulseDevice([25]);
          statusText = dictionary.chain.invalid;
          syncChainUI();
          return;
        }
        if (usedWords.has(guess)) {
          pulseDevice([25]);
          statusText = dictionary.chain.used;
          syncChainUI();
          return;
        }

        currentWord = guess;
        usedWords.add(guess);
        score += 1;
        currentGuess = "";
        statusText = dictionary.chain.nextWord;
        const best = Math.max(Number(localStorage.getItem(bestKey) || "0"), score);
        localStorage.setItem(bestKey, String(best));
        saveLastPlayed("word-chain");
        pulseDevice([12]);
        syncChainUI();
        input.focus();
      });

      document.getElementById("chain-guess").addEventListener("input", function (event) {
        currentGuess = event.target.value;
      });
    }

    function renderEnd() {
      const best = Number(localStorage.getItem(bestKey) || "0");
      app.innerHTML = layout(
        `
        <section class="panel end-card">
          <h1>${personalCelebratePrompt ? `${personalCelebratePrompt} ${dictionary.chain.gameOver}` : dictionary.chain.gameOver}</h1>
          <p>${dictionary.common.score}: ${score} | ${dictionary.common.best}: ${best}</p>
          <aside class="ad-placeholder">${dictionary.common.adLabel}: ${dictionary.common.endScreen}</aside>
          <button class="primary-button" id="restart-chain">${dictionary.common.playAgain}</button>
        </section>
      `,
        dictionary.home.chainHero,
      );
      bindLanguageSwitcher();
      document.getElementById("restart-chain").addEventListener("click", renderWordChain);
    }

    drawShell();
    intervalId = window.setInterval(function () {
      secondsLeft -= 1;
      if (secondsLeft <= 0) {
        clearInterval(intervalId);
        renderEnd();
        return;
      }
      syncChainUI();
    }, 1000);
  }

  function renderCategoryBlitz() {
    const displayName = getDisplayName();
    const personalCategoryPrompt = getPlayerPrompt(displayName, "typo");
    const personalCelebratePrompt = getPlayerPrompt(displayName, "celebrate");
    const bestKey = getScopedKey("word-game-category-best", currentLanguage);
    const rounds = categoryRounds.slice(0, 10);
    let roundIndex = 0;
    let score = 0;

    function draw() {
      const round = rounds[roundIndex];
      app.innerHTML = layout(
        `
        <section class="panel game-screen category-screen">
          <header class="section-header">
            <div>
              <h1>${dictionary.category.title}</h1>
              <p>${dictionary.category.body}</p>
              ${personalCategoryPrompt ? `<p class="player-note">${personalCategoryPrompt}</p>` : ""}
            </div>
            <div class="stats-row">
              <p class="stat-pill">${dictionary.common.question}: ${roundIndex + 1}/${rounds.length}</p>
              <p class="stat-pill">${dictionary.common.score}: ${score}</p>
            </div>
          </header>
          <p class="subtle">${dictionary.category.instruction}</p>
          <section class="panel category-card">
            <p class="card-kicker">${dictionary.common.question}</p>
            <h2>${round.category}</h2>
          </section>
          <div class="option-grid">
            ${round.options
              .map((option) => `<button class="option-button" type="button" data-option="${option}">${option}</button>`)
              .join("")}
          </div>
        </section>
      `,
        dictionary.home.categoryHero,
      );
      bindLanguageSwitcher();

      app.querySelectorAll("[data-option]").forEach(function (button) {
        button.addEventListener(
          "click",
          function () {
            const selected = button.getAttribute("data-option");
            const buttons = Array.from(app.querySelectorAll("[data-option]"));
            buttons.forEach(function (item) {
              const isTarget = item.getAttribute("data-option") === round.answer;
              if (isTarget) {
                item.classList.add("correct");
              }
              if (item === button && !isTarget) {
                item.classList.add("wrong");
              }
              item.disabled = true;
            });

            if (selected === round.answer) {
              score += 1;
              const best = Math.max(Number(localStorage.getItem(bestKey) || "0"), score);
              localStorage.setItem(bestKey, String(best));
              pulseDevice([12]);
            } else {
              pulseDevice([25]);
            }
            saveLastPlayed("category-blitz");

            const nextButton = document.createElement("button");
            nextButton.className = "next-button";
            nextButton.textContent = dictionary.category.next;
            nextButton.addEventListener("click", function () {
              roundIndex += 1;
              if (roundIndex >= rounds.length) {
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
          <h1>${personalCelebratePrompt ? `${personalCelebratePrompt} ${dictionary.category.gameOver}` : dictionary.category.gameOver}</h1>
          <p>${dictionary.common.score}: ${score} | ${dictionary.common.best}: ${best}</p>
          <aside class="ad-placeholder">${dictionary.common.adLabel}: ${dictionary.common.endScreen}</aside>
          <button class="primary-button" id="restart-category">${dictionary.common.playAgain}</button>
        </section>
      `,
        dictionary.home.categoryHero,
      );
      bindLanguageSwitcher();
      document.getElementById("restart-category").addEventListener("click", renderCategoryBlitz);
    }

    draw();
  }

  function renderMiniCrossword() {
    const displayName = getDisplayName();
    const personalCrosswordPrompt = getPlayerPrompt(displayName, "daily");
    const personalCelebratePrompt = getPlayerPrompt(displayName, "celebrate");
    const crosswordStateKey = getScopedKey("word-game-crossword-state", currentLanguage);
    const activeCrossword = getActiveCrossword(currentLanguage);
    const puzzle = activeCrossword.puzzle;
    const builtPuzzle = buildCrosswordPuzzle(puzzle);
    const todayKey = getTodayKey();
    const puzzleSignature = `${currentLanguage}:${activeCrossword.activeIndex}:${puzzle.entries
      .map(function (entry) {
        return `${entry.direction}-${entry.number}-${entry.answer}`;
      })
      .join("|")}`;
    const savedState = JSON.parse(localStorage.getItem(crosswordStateKey) || "null");
    const state =
      savedState && savedState.date === todayKey && savedState.puzzleSignature === puzzleSignature
        ? savedState
        : {
            date: todayKey,
            puzzleSignature,
            letters: {},
            message: dictionary.crossword.instruction,
            checked: false,
            completed: false,
          };

    function persist() {
      localStorage.setItem(crosswordStateKey, JSON.stringify(state));
    }

    function getCellKey(row, col) {
      return `${row}-${col}`;
    }

    function getOrderedInputs() {
      return Array.from(document.querySelectorAll(".crossword-grid input"));
    }

    function countCorrectLetters() {
      return builtPuzzle.cells.reduce(function (count, cell, index) {
        if (cell.blocked) {
          return count;
        }
        const row = Math.floor(index / builtPuzzle.size);
        const col = index % builtPuzzle.size;
        const value = state.letters[getCellKey(row, col)];
        return count + (value === cell.solution ? 1 : 0);
      }, 0);
    }

    function finishIfSolved() {
      if (countCorrectLetters() === builtPuzzle.totalFillable) {
        state.completed = true;
        state.checked = true;
        state.message = dictionary.crossword.complete;
        saveLastPlayed("mini-crossword");
        pulseDevice([12, 30, 12]);
        persist();
        return true;
      }
      return false;
    }

    function draw() {
      const filledCount = Object.values(state.letters).filter(Boolean).length;
      const clueMarkup = function (direction, label) {
        return `
          <div class="panel crossword-clue-card">
            <p class="card-kicker">${label}</p>
            <ul class="privacy-list">
              ${builtPuzzle.entries
                .filter(function (entry) {
                  return entry.direction === direction;
                })
                .map(function (entry) {
                  return `<li><strong>${entry.number}.</strong> ${entry.clue}</li>`;
                })
                .join("")}
            </ul>
          </div>
        `;
      };

      app.innerHTML = layout(
        `
        <section class="panel game-screen crossword-screen">
          <header class="section-header">
            <div>
              <h1>${dictionary.crossword.title}</h1>
              <p>${dictionary.crossword.body}</p>
              ${personalCrosswordPrompt ? `<p class="player-note">${personalCrosswordPrompt}</p>` : ""}
            </div>
            <div class="stats-row">
              <p class="stat-pill">${dictionary.crossword.progress}: ${filledCount}/${builtPuzzle.totalFillable}</p>
            </div>
          </header>
          <p class="subtle">${state.message}</p>
          <div class="crossword-layout">
            <section class="panel crossword-board">
              <div class="crossword-grid" style="grid-template-columns: repeat(${builtPuzzle.size}, minmax(0, 1fr));">
                ${builtPuzzle.cells
                  .map(function (cell, index) {
                    if (cell.blocked) {
                      return '<div class="crossword-cell blocked" aria-hidden="true"></div>';
                    }
                    const row = Math.floor(index / builtPuzzle.size);
                    const col = index % builtPuzzle.size;
                    const key = getCellKey(row, col);
                    const letter = state.letters[key] || "";
                    const wrongClass = state.checked && letter && letter !== cell.solution ? " wrong" : "";
                    return `
                      <label class="crossword-cell${wrongClass}">
                        ${cell.number ? `<span class="crossword-number">${cell.number}</span>` : ""}
                        <input
                          data-row="${row}"
                          data-col="${col}"
                          maxlength="1"
                          autocapitalize="characters"
                          autocomplete="off"
                          spellcheck="false"
                          inputmode="text"
                          value="${letter ? displayWord(letter) : ""}"
                        />
                      </label>
                    `;
                  })
                  .join("")}
              </div>
              <div class="crossword-actions">
                <button class="primary-button" type="button" id="check-crossword">${dictionary.crossword.check}</button>
                <button class="ghost-button" type="button" id="reveal-crossword">${dictionary.crossword.reveal}</button>
                ${
                  activeCrossword.hasNext
                    ? `<button class="ghost-button" type="button" id="next-crossword">${dictionary.crossword.next}</button>`
                    : ""
                }
              </div>
            </section>
            <section class="crossword-clues">
              ${clueMarkup("across", dictionary.crossword.across)}
              ${clueMarkup("down", dictionary.crossword.down)}
            </section>
          </div>
          ${
            state.completed
              ? `
                <section class="panel ladder-celebration">
                  <p class="card-kicker">${dictionary.crossword.title}</p>
                  <h2>${personalCelebratePrompt ? `${personalCelebratePrompt} ${dictionary.crossword.complete}` : dictionary.crossword.complete}</h2>
                </section>
              `
              : ""
          }
        </section>
      `,
        dictionary.home.crosswordHero,
      );
      bindLanguageSwitcher();

      const inputs = getOrderedInputs();
      if (inputs[0]) {
        requestAnimationFrame(function () {
          inputs[0].focus();
        });
      }

      inputs.forEach(function (input, position) {
        input.addEventListener("input", function (event) {
          const row = Number(input.getAttribute("data-row"));
          const col = Number(input.getAttribute("data-col"));
          const key = getCellKey(row, col);
          const value = Array.from(normalizeWord(event.target.value)).slice(-1)[0] || "";

          if (value) {
            state.letters[key] = value;
            input.value = displayWord(value);
            const nextInput = inputs[position + 1];
            if (nextInput) {
              nextInput.focus();
              nextInput.select();
            }
          } else {
            delete state.letters[key];
            input.value = "";
          }
          state.checked = false;
          state.completed = false;
          state.message = `${dictionary.crossword.progress}: ${Object.values(state.letters).filter(Boolean).length}/${builtPuzzle.totalFillable}`;
          persist();
        });

        input.addEventListener("keydown", function (event) {
          if (event.key === "Backspace" && !input.value) {
            const previousInput = inputs[position - 1];
            if (previousInput) {
              previousInput.focus();
              previousInput.select();
            }
          }
        });
      });

      document.getElementById("check-crossword").addEventListener("click", function () {
        state.checked = true;
        if (!finishIfSolved()) {
          state.message = `${dictionary.crossword.progress}: ${countCorrectLetters()}/${builtPuzzle.totalFillable}`;
          pulseDevice([25]);
          persist();
          draw();
        } else {
          draw();
        }
      });

      document.getElementById("reveal-crossword").addEventListener("click", function () {
        const nextCell = builtPuzzle.cells.find(function (cell, index) {
          if (cell.blocked) {
            return false;
          }
          const row = Math.floor(index / builtPuzzle.size);
          const col = index % builtPuzzle.size;
          return state.letters[getCellKey(row, col)] !== cell.solution;
        });

        if (!nextCell) {
          finishIfSolved();
          draw();
          return;
        }

        const index = builtPuzzle.cells.indexOf(nextCell);
        const row = Math.floor(index / builtPuzzle.size);
        const col = index % builtPuzzle.size;
        state.letters[getCellKey(row, col)] = nextCell.solution;
        state.checked = false;
        state.message = `${dictionary.crossword.progress}: ${Object.values(state.letters).filter(Boolean).length}/${builtPuzzle.totalFillable}`;
        pulseDevice([12]);
        finishIfSolved();
        persist();
        draw();
      });

      const nextButton = document.getElementById("next-crossword");
      if (nextButton) {
        nextButton.addEventListener("click", function () {
          switchActiveCrossword(currentLanguage);
          renderMiniCrossword();
        });
      }
    }

    persist();
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
    } else if (currentPage === "word-chain") {
      renderWordChain();
    } else if (currentPage === "category-blitz") {
      renderCategoryBlitz();
    } else if (currentPage === "mini-crossword") {
      renderMiniCrossword();
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
