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
    const activeIndex = Math.min(baseIndex + bonusOffset, pool.length - 1);
    return {
      puzzle: pool[activeIndex],
      bonusOffset,
      activeIndex,
      hasNextBonus: activeIndex < pool.length - 1,
    };
  }

  function unlockNextBonus(language) {
    const key = getSessionKey("word-game-daily-ladder-bonus", language);
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

  function layout(content, heroNote) {
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
                return `<button type="button" data-lang="${language}" class="${active}">${language.toUpperCase()}</button>`;
              })
              .join("")}
          </div>
        </header>
        <aside class="ad-placeholder top-banner">${dictionary.common.adLabel}: ${dictionary.common.topBanner}</aside>
        <div class="shell-body">
          <main class="main-content">
            <section class="panel hero-shell">
              <p class="eyebrow">${heroNote || dictionary.home.eyebrow}</p>
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
            ${content}
            <footer class="panel site-footer">
              <a href="${pathFor(currentLanguage, "privacy")}">${dictionary.common.privacy}</a>
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
    const hintText = hintVisible ? puzzle.clues[nextExpected] || displayWord(nextExpected) : "";
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
          <h2>${dictionary.daily.win}</h2>
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

    app.innerHTML = layout(
      `
      <section class="panel game-screen ladder-screen">
        <header class="section-header">
          <div>
            <h1>${dictionary.daily.title}</h1>
            <p>${dictionary.daily.body}</p>
          </div>
          <div class="stats-row">
            <p class="stat-pill">${dictionary.daily.streak}: ${streak}</p>
            <p class="stat-pill">${dictionary.daily.moves}: ${state.steps.length - 1}/${maxMoves}</p>
            <p class="stat-pill">${dictionary.daily.bonusLabel}: ${ladderState.bonusOffset + 1}</p>
          </div>
        </header>
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
            <p>${hintText}</p>
            <span>${hintVisible ? dictionary.daily.retryHint : "&nbsp;"}</span>
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
        unlockNextBonus(currentLanguage);
        renderDailyLadder();
      });
    }

    function commitInvalid(message, countTowardHint) {
      if (countTowardHint) {
        state.invalidAttemptCount += 1;
      }
      state.flashMessage =
        state.invalidAttemptCount >= 2 && nextExpected ? dictionary.daily.retryHint : message;
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
          <h1>${dictionary.scramble.gameOver}</h1>
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
          <h1>${dictionary.typo.gameOver}</h1>
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
    app.innerHTML = layout(
      `
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
        </ul>
        <a class="cta-link" href="${pathFor(currentLanguage, "home")}">${dictionary.common.backHome}</a>
      </section>
    `,
      dictionary.common.privacy,
    );
    bindLanguageSwitcher();
  }

  function renderAbout() {
    app.innerHTML = layout(
      `
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
    `,
      dictionary.common.about,
    );
    bindLanguageSwitcher();
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
    } else {
      renderTypoHunt();
    }
  }

  boot();
})();
