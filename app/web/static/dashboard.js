const DASHBOARD_CONFIG = window.DASHBOARD_CONFIG || {};
        const SYMBOLS = DASHBOARD_CONFIG.symbols || ['SOLUSDT'];
        let selectedSymbol = DASHBOARD_CONFIG.defaultSymbol || SYMBOLS[0];
        let minSpreadPct = Number(DASHBOARD_CONFIG.minSpreadPct || 0);
        let executionSize = 10;
        let language = localStorage.getItem('dashboardLanguage') || 'en';

        const TRANSLATIONS = {
            en: {
                languageTitle: 'Choose language / Выберите язык',
                languageText: 'Select dashboard and documentation language.',
                eyebrow: 'Market intelligence',
                title: 'Crypto Arbitrage Analytics',
                subtitle: 'Real-time multi-symbol monitor across Binance, Bybit, OKX, and Gate.io. The dashboard highlights bid/ask-based estimates, scoring, and stale data.',
                symbol: 'Symbol',
                minSpread: 'Min spread %',
                executionSize: 'Execution size',
                docs: 'Docs',
                bestSpread: 'Best spread',
                freshExchanges: 'Fresh exchanges',
                freshHelp: 'Only fresh prices are used for spread',
                lastUpdate: 'Last update',
                localTime: 'Local dashboard time',
                executionTitle: 'Order-book execution estimate',
                executionNote: 'Walks ask/bid levels and compares raw spread with executable net result',
                verdictLabel: 'Execution verdict',
                route: 'Route',
                rawSpread: 'Raw spread',
                vwapSpread: 'VWAP spread',
                feesImpact: 'Fees',
                netResult: 'Net result',
                maxProfitableSize: 'Max profitable size',
                snapshotSync: 'Snapshot sync',
                scenarioLive: 'Live market',
                scenarioProfitable: 'Profitable',
                scenarioSlippage: 'Slippage trap',
                scenarioLiquidity: 'Low liquidity',
                scenarioStale: 'Stale data',
                buyAsks: 'Buy asks',
                sellBids: 'Sell bids',
                price: 'Price',
                filled: 'Filled',
                depth: 'Depth',
                historyTitle: 'History summary',
                historyNote: 'Signals saved in SQLite during the last hour',
                signals: 'Signals',
                maxSpread: 'Max spread',
                avgSpread: 'Avg spread',
                maxNet: 'Max net',
                avgScore: 'Avg score',
                time: 'Time',
                spread: 'Spread',
                net: 'Net',
                score: 'Score',
                pricesTitle: 'Exchange prices',
                pricesNote: 'Top-of-book bid/ask from public streams',
                exchange: 'Exchange',
                bid: 'Bid',
                ask: 'Ask',
                age: 'Age',
                status: 'Status',
                opportunityTitle: 'Estimated opportunity',
                opportunityNote: 'Simple fee-aware calculation',
                buyOn: 'Buy on',
                sellOn: 'Sell on',
                grossPnl: 'Gross PnL',
                netEstimate: 'Net estimate',
                mlQuality: 'ML quality',
                mlSignalAnalysis: 'ML signal analysis',
                probability: 'Probability',
                confidence: 'Confidence',
                topBookWarning: 'Estimate uses top-of-book bid/ask. Real execution still needs deeper order-book simulation, slippage, and transfer costs.',
                localDashboard: 'Local analytical dashboard',
                apiFooter: 'API: /api/health /api/prices /api/opportunity',
                waiting: 'Waiting',
                connected: 'Connected',
                disconnected: 'Disconnected',
                noFreshRoute: 'No fresh route yet',
                live: 'Live',
                stale: 'Stale',
                filtered: 'Filtered',
                belowThreshold: 'Below threshold',
                executable: 'Executable',
                risky: 'Risky',
                rejected: 'Rejected',
                noExecution: 'No executable route for the selected size.',
                buyAsksOn: 'Buy asks on',
                sellBidsOn: 'Sell bids on',
                scoreLabel: 'Score',
                fillLabel: 'Fill',
                slippageLabel: 'Slippage',
                snapshotSkewLabel: 'Snapshot skew',
                ms: 'ms',
                recommendation_show_to_user: 'show to user',
                recommendation_watch: 'watch',
                recommendation_ignore: 'ignore',
                recommendation_wait_for_data: 'wait for data',
                quality_strong: 'strong',
                quality_watch: 'watch',
                quality_weak: 'weak',
                quality_no_signal: 'no signal',
                risk_net_result: 'net result is not positive after fees',
                risk_fees: 'fees consume a large part of gross spread',
                risk_unknown_liquidity: 'visible liquidity size is unknown',
                risk_small_liquidity: 'visible liquidity is small',
                risk_narrow_spread: 'spread is too narrow',
                risk_no_major: 'no major top-of-book risk detected',
                reason_net_positive: 'net profit remains positive after fees and depth simulation',
                reason_net_negative: 'net profit is not positive after fees and depth simulation',
                reason_vwap_positive: 'VWAP sell price is above VWAP buy price',
                reason_full_fill: 'target size is fully executable on visible levels',
                reason_not_full_fill: 'target size is not fully executable on visible levels',
                reason_slippage_low: 'combined slippage is low',
                reason_slippage_moderate: 'combined slippage is moderate',
                reason_slippage_high: 'combined slippage is high',
                reason_few_levels: 'execution uses only a few order-book levels',
                rejectedLiquidity: 'Rejected: visible order-book depth cannot fill the selected size on both sides.',
                rejectedStale: 'Rejected: order-book snapshots are older than the allowed freshness window.',
                to: 'to',
            },
            ru: {
                languageTitle: 'Выберите язык',
                languageText: 'Выберите язык dashboard и документации.',
                eyebrow: 'Аналитика рынка',
                title: 'Crypto Arbitrage Analytics',
                subtitle: 'Мониторинг нескольких монет в реальном времени на Binance, Bybit, OKX и Gate.io. Dashboard показывает оценки по bid/ask, score и устаревшие данные.',
                symbol: 'Монета',
                minSpread: 'Мин. спред %',
                executionSize: 'Объем сделки',
                docs: 'Документация',
                bestSpread: 'Лучший спред',
                freshExchanges: 'Свежие биржи',
                freshHelp: 'Для спреда используются только свежие цены',
                lastUpdate: 'Последнее обновление',
                localTime: 'Локальное время dashboard',
                executionTitle: 'Оценка исполнения по стаканам',
                executionNote: 'Проходит по уровням ask/bid и сравнивает сырой спред с чистым результатом',
                verdictLabel: 'Вердикт исполнения',
                route: 'Маршрут',
                rawSpread: 'Сырой спред',
                vwapSpread: 'VWAP-спред',
                feesImpact: 'Комиссии',
                netResult: 'Чистый результат',
                maxProfitableSize: 'Макс. прибыльный объем',
                snapshotSync: 'Синхронизация стаканов',
                scenarioLive: 'Текущий рынок',
                scenarioProfitable: 'Прибыльный',
                scenarioSlippage: 'Ловушка проскальзывания',
                scenarioLiquidity: 'Мало ликвидности',
                scenarioStale: 'Старые данные',
                buyAsks: 'Покупка по ask',
                sellBids: 'Продажа по bid',
                price: 'Цена',
                filled: 'Заполнено',
                depth: 'Глубина',
                historyTitle: 'История сигналов',
                historyNote: 'Сигналы, сохраненные в SQLite за последний час',
                signals: 'Сигналы',
                maxSpread: 'Макс. спред',
                avgSpread: 'Средний спред',
                maxNet: 'Макс. чистая прибыль',
                avgScore: 'Средний score',
                time: 'Время',
                spread: 'Спред',
                net: 'Чистый результат',
                score: 'Score',
                pricesTitle: 'Цены на биржах',
                pricesNote: 'Лучшие bid/ask из публичных потоков',
                exchange: 'Биржа',
                bid: 'Bid',
                ask: 'Ask',
                age: 'Возраст',
                status: 'Статус',
                opportunityTitle: 'Оценка возможности',
                opportunityNote: 'Простой расчет с учетом комиссий',
                buyOn: 'Купить на',
                sellOn: 'Продать на',
                grossPnl: 'Грязная прибыль',
                netEstimate: 'Чистая оценка',
                mlQuality: 'ML-качество',
                mlSignalAnalysis: 'ML-анализ сигнала',
                probability: 'Вероятность',
                confidence: 'Уверенность',
                topBookWarning: 'Оценка использует лучший bid/ask. Реальное исполнение требует проверки глубины стакана, проскальзывания и затрат на перевод.',
                localDashboard: 'Локальный аналитический dashboard',
                apiFooter: 'API: /api/health /api/prices /api/opportunity',
                waiting: 'Ожидание',
                connected: 'Подключено',
                disconnected: 'Отключено',
                noFreshRoute: 'Свежего маршрута пока нет',
                live: 'Актуально',
                stale: 'Устарело',
                filtered: 'Отфильтровано',
                belowThreshold: 'Ниже порога',
                executable: 'Исполнимо',
                risky: 'Рискованно',
                rejected: 'Отклонено',
                noExecution: 'Нет исполнимого маршрута для выбранного объема.',
                buyAsksOn: 'Покупка по ask на',
                sellBidsOn: 'Продажа по bid на',
                scoreLabel: 'Score',
                fillLabel: 'Заполнение',
                slippageLabel: 'Проскальзывание',
                snapshotSkewLabel: 'Рассинхрон стаканов',
                ms: 'мс',
                recommendation_show_to_user: 'показать пользователю',
                recommendation_watch: 'наблюдать',
                recommendation_ignore: 'игнорировать',
                recommendation_wait_for_data: 'ждать данные',
                quality_strong: 'сильный',
                quality_watch: 'наблюдать',
                quality_weak: 'слабый',
                quality_no_signal: 'нет сигнала',
                risk_net_result: 'чистый результат неположительный после комиссий',
                risk_fees: 'комиссии съедают большую часть грязного спреда',
                risk_unknown_liquidity: 'объем видимой ликвидности неизвестен',
                risk_small_liquidity: 'видимая ликвидность маленькая',
                risk_narrow_spread: 'спред слишком узкий',
                risk_no_major: 'серьезных top-of-book рисков не найдено',
                reason_net_positive: 'чистая прибыль остается положительной после комиссий и симуляции стакана',
                reason_net_negative: 'чистая прибыль неположительная после комиссий и симуляции стакана',
                reason_vwap_positive: 'VWAP-цена продажи выше VWAP-цены покупки',
                reason_full_fill: 'целевой объем полностью исполним на видимых уровнях',
                reason_not_full_fill: 'целевой объем не исполним полностью на видимых уровнях',
                reason_slippage_low: 'общее проскальзывание низкое',
                reason_slippage_moderate: 'общее проскальзывание умеренное',
                reason_slippage_high: 'общее проскальзывание высокое',
                reason_few_levels: 'исполнение использует только несколько уровней стакана',
                rejectedLiquidity: 'Отклонено: видимой глубины стакана недостаточно для выбранного объема с обеих сторон.',
                rejectedStale: 'Отклонено: снимки стаканов старше допустимого окна свежести.',
                to: 'в',
            },
        };

        const t = (key) => TRANSLATIONS[language][key] || TRANSLATIONS.en[key] || key;
        const translateQuality = (value) => t('quality_' + value) || value || '--';
        const translateRecommendation = (value) => t('recommendation_' + value) || value || '--';
        const translateRisk = (risk) => {
            const riskMap = {
                'net result is not positive after fees': 'risk_net_result',
                'fees consume a large part of gross spread': 'risk_fees',
                'visible liquidity size is unknown': 'risk_unknown_liquidity',
                'visible liquidity is small': 'risk_small_liquidity',
                'spread is too narrow': 'risk_narrow_spread',
                'no major top-of-book risk detected': 'risk_no_major',
            };
            return riskMap[risk] ? t(riskMap[risk]) : risk;
        };
        const translateReason = (reason) => {
            const reasonMap = {
                'net profit remains positive after fees and depth simulation': 'reason_net_positive',
                'net profit is not positive after fees and depth simulation': 'reason_net_negative',
                'VWAP sell price is above VWAP buy price': 'reason_vwap_positive',
                'target size is fully executable on visible levels': 'reason_full_fill',
                'target size is not fully executable on visible levels': 'reason_not_full_fill',
                'combined slippage is low': 'reason_slippage_low',
                'combined slippage is moderate': 'reason_slippage_moderate',
                'combined slippage is high': 'reason_slippage_high',
                'execution uses only a few order-book levels': 'reason_few_levels',
            };
            return reasonMap[reason] ? t(reasonMap[reason]) : reason;
        };
        const translateExecutionNote = (note) => {
            if (!note) {
                return t('noExecution');
            }
            if (note.startsWith('Rejected: visible order-book depth')) {
                return t('rejectedLiquidity');
            }
            if (note.startsWith('Rejected: order-book snapshots')) {
                return t('rejectedStale');
            }
            return note;
        };

        const applyLanguage = (nextLanguage, persist = true, closeModal = true) => {
            language = nextLanguage;
            if (persist) {
                localStorage.setItem('dashboardLanguage', language);
            }
            document.documentElement.lang = language;
            document.querySelectorAll('[data-i18n]').forEach((node) => {
                node.textContent = t(node.dataset.i18n);
            });
            document.getElementById('docs-link').textContent = t('docs');
            document.getElementById('docs-link').href = language === 'ru' ? '/docs/ru' : '/docs/en';
            document.getElementById('lang-en').classList.toggle('active', language === 'en');
            document.getElementById('lang-ru').classList.toggle('active', language === 'ru');
            updateScenarioButtons();
            if (closeModal) {
                document.getElementById('language-modal').classList.remove('open');
            }
        };

        const formatPrice = (value) => value === null || value === undefined
            ? t('waiting')
            : '$' + value.toFixed(2);

        const formatMoney = (value) => value === null || value === undefined
            ? '--'
            : (value >= 0 ? '+$' : '-$') + Math.abs(value).toFixed(2);

        const symbolSelect = document.getElementById('symbol-select');
        document.querySelectorAll('[data-set-lang]').forEach((button) => {
            button.addEventListener('click', () => applyLanguage(button.dataset.setLang));
        });
        if (!localStorage.getItem('dashboardLanguage')) {
            document.getElementById('language-modal').classList.add('open');
        }

        for (const symbol of SYMBOLS) {
            const option = document.createElement('option');
            option.value = symbol;
            option.textContent = symbol;
            if (symbol === selectedSymbol) {
                option.selected = true;
            }
            symbolSelect.appendChild(option);
        }
        symbolSelect.addEventListener('change', () => {
            selectedSymbol = symbolSelect.value;
            resetOpportunity();
            updateHistory();
        });

        const minSpreadInput = document.getElementById('min-spread');
        minSpreadInput.value = minSpreadPct;
        minSpreadInput.addEventListener('input', () => {
            minSpreadPct = Number(minSpreadInput.value || 0);
        });
        const executionSizeInput = document.getElementById('execution-size');
        executionSizeInput.addEventListener('input', () => {
            executionSize = Number(executionSizeInput.value || 10);
            executionScenario = 'live';
            updateScenarioButtons();
        });

        let executionScenario = 'live';
        const scenarioSizes = {
            live: 10,
            profitable: 10,
            slippage: 20,
            liquidity: 10,
            stale: 10,
        };
        const updateScenarioButtons = () => {
            document.querySelectorAll('[data-scenario]').forEach((button) => {
                button.classList.toggle('active', button.dataset.scenario === executionScenario);
                if (button.dataset.i18n) {
                    button.textContent = t(button.dataset.i18n);
                }
            });
        };
        document.querySelectorAll('[data-scenario]').forEach((button) => {
            button.addEventListener('click', () => {
                executionScenario = button.dataset.scenario;
                executionSize = scenarioSizes[executionScenario] || 10;
                executionSizeInput.value = executionSize;
                updateScenarioButtons();
                updateExecution();
            });
        });
        applyLanguage(language, false, false);

        const resetOpportunity = () => {
            document.getElementById('buy-on').textContent = '--';
            document.getElementById('sell-on').textContent = '--';
            document.getElementById('gross-pnl').textContent = '--';
            document.getElementById('fees').textContent = '--';
            document.getElementById('net-pnl').textContent = '--';
            document.getElementById('spread-pct').textContent = '--';
            document.getElementById('score').textContent = '--';
            document.getElementById('quality').textContent = '--';
            renderMlInsight(null);
        };

        const renderMlInsight = (quality) => {
            const probability = quality ? quality.probability || 0 : 0;
            const confidence = quality ? quality.confidence || 0 : 0;
            document.getElementById('ml-model').textContent = quality ? quality.model : '--';
            document.getElementById('ml-probability').textContent = quality ? Math.round(probability * 100) + '%' : '--';
            document.getElementById('ml-confidence').textContent = quality ? Math.round(confidence * 100) + '%' : '--';
            document.getElementById('ml-probability-bar').style.width = Math.round(probability * 100) + '%';
            document.getElementById('ml-confidence-bar').style.width = Math.round(confidence * 100) + '%';

            const recommendation = document.getElementById('ml-recommendation');
            recommendation.textContent = quality ? translateRecommendation(quality.recommendation) : '--';
            recommendation.className = 'pill ' + (quality && quality.quality === 'strong' ? 'live' : 'stale');

            const list = document.getElementById('ml-risk-list');
            list.innerHTML = '';
            const risks = quality ? quality.risk_factors || [] : [];
            for (const risk of risks.slice(0, 4)) {
                const item = document.createElement('li');
                item.textContent = translateRisk(risk);
                list.appendChild(item);
            }
        };

        const renderRows = (exchanges) => {
            const tbody = document.getElementById('exchange-rows');
            tbody.innerHTML = '';

            for (const [exchange, item] of Object.entries(exchanges)) {
                const live = item && item.live;
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="exchange">${exchange}</td>
                    <td class="price">${item ? formatPrice(item.bid_price) : t('waiting')}</td>
                    <td class="price">${item ? formatPrice(item.ask_price) : t('waiting')}</td>
                    <td>${item ? item.age : '--'}</td>
                    <td><span class="pill ${live ? 'live' : 'stale'}">${live ? t('live') : t('stale')}</span></td>
                `;
                tbody.appendChild(row);
            }
        };

        const percentText = (value) => value === null || value === undefined ? '--' : value.toFixed(4) + '%';

        const setBar = (id, value, maxValue) => {
            const element = document.getElementById(id);
            const width = maxValue > 0 ? Math.min(100, Math.abs(value) / maxValue * 100) : 0;
            element.style.width = width + '%';
            element.className = 'waterfall-fill ' + (value >= 0 ? 'positive' : 'negative');
        };

        const renderFillRows = (targetId, fills) => {
            const tbody = document.getElementById(targetId);
            tbody.innerHTML = '';
            if (!fills || fills.length === 0) {
                const row = document.createElement('tr');
                row.innerHTML = '<td>--</td><td>--</td><td>--</td>';
                tbody.appendChild(row);
                return;
            }
            for (const fill of fills) {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="price">$${fill.price.toFixed(4)}</td>
                    <td>${fill.filled_size.toFixed(4)} / ${fill.available_size.toFixed(4)}</td>
                    <td>
                        <div class="fill-bar">
                            <span style="width: ${Math.min(100, fill.fill_pct).toFixed(1)}%"></span>
                        </div>
                    </td>
                `;
                tbody.appendChild(row);
            }
        };

        const resetExecution = (detail) => {
            document.getElementById('exec-route').textContent = '--';
            document.getElementById('exec-raw').textContent = '--';
            document.getElementById('exec-vwap').textContent = '--';
            document.getElementById('exec-net').textContent = '--';
            document.getElementById('exec-max-size').textContent = '--';
            document.getElementById('exec-sync').textContent = '--';
            document.getElementById('waterfall-raw').textContent = '--';
            document.getElementById('waterfall-vwap').textContent = '--';
            document.getElementById('waterfall-fees').textContent = '--';
            document.getElementById('waterfall-net').textContent = '--';
            setBar('bar-raw', 0, 1);
            setBar('bar-vwap', 0, 1);
            setBar('bar-fees', 0, 1);
            setBar('bar-net', 0, 1);
            renderFillRows('buy-book-rows', []);
            renderFillRows('sell-book-rows', []);
            const verdict = document.getElementById('exec-verdict');
            verdict.className = 'verdict bad';
            document.getElementById('exec-verdict-value').textContent = t('rejected');
            document.getElementById('exec-verdict-detail').textContent = translateExecutionNote(detail);
        };

        const updateOpportunity = async () => {
            try {
                const response = await fetch('/api/opportunity?symbol=' + encodeURIComponent(selectedSymbol));
                const payload = await response.json();
                const item = payload.opportunity;
                const quality = payload.quality;

                if (!item) {
                    resetOpportunity();
                    return;
                }

                if (Math.abs(item.spread_pct) < minSpreadPct) {
                    resetOpportunity();
                    document.getElementById('buy-on').textContent = t('filtered');
                    document.getElementById('sell-on').textContent = t('belowThreshold');
                    return;
                }

                document.getElementById('buy-on').textContent = item.buy_on;
                document.getElementById('sell-on').textContent = item.sell_on;
                document.getElementById('gross-pnl').textContent = formatMoney(item.gross_profit_usd);
                document.getElementById('fees').textContent = '$' + item.estimated_fees_usd.toFixed(2);

                const net = document.getElementById('net-pnl');
                net.textContent = formatMoney(item.estimated_net_profit_usd);
                net.className = 'fact-value ' + (item.estimated_net_profit_usd >= 0 ? 'positive' : 'negative');

                document.getElementById('spread-pct').textContent = item.spread_pct.toFixed(3) + '%';
                document.getElementById('score').textContent = item.score.toFixed(1) + ' / 100';
                document.getElementById('quality').textContent = quality ? translateQuality(quality.quality) : '--';
                renderMlInsight(quality);
            } catch (error) {
                console.error('Failed to load opportunity', error);
            }
        };

        const updateHistory = async () => {
            try {
                const [historyResponse, opportunitiesResponse] = await Promise.all([
                    fetch('/api/history?symbol=' + encodeURIComponent(selectedSymbol)),
                    fetch('/api/opportunities?symbol=' + encodeURIComponent(selectedSymbol) + '&limit=8')
                ]);
                const item = await historyResponse.json();
                const opportunities = await opportunitiesResponse.json();
                document.getElementById('history-count').textContent = item.opportunity_count ?? 0;
                document.getElementById('history-max-spread').textContent =
                    item.max_spread_pct === null || item.max_spread_pct === undefined ? '--' : item.max_spread_pct.toFixed(4) + '%';
                document.getElementById('history-avg-spread').textContent =
                    item.avg_spread_pct === null || item.avg_spread_pct === undefined ? '--' : item.avg_spread_pct.toFixed(4) + '%';
                document.getElementById('history-max-net').textContent =
                    item.max_net_profit_usd === null || item.max_net_profit_usd === undefined ? '--' : formatMoney(item.max_net_profit_usd);
                document.getElementById('history-avg-score').textContent =
                    item.avg_score === null || item.avg_score === undefined ? '--' : item.avg_score.toFixed(1);

                const tbody = document.getElementById('recent-opportunities');
                tbody.innerHTML = '';
                for (const row of opportunities.opportunities || []) {
                    const tr = document.createElement('tr');
                    const time = new Date(row.ts * 1000).toLocaleTimeString();
                    tr.innerHTML = `
                        <td>${time}</td>
                        <td>${row.buy_on} ${t('to')} ${row.sell_on}</td>
                        <td>${row.spread_pct.toFixed(4)}%</td>
                        <td>${formatMoney(row.estimated_net_profit_usd)}</td>
                        <td>${row.score.toFixed(1)}</td>
                    `;
                    tbody.appendChild(tr);
                }
            } catch (error) {
                console.error('Failed to load history', error);
            }
        };

        const updateExecution = async () => {
            try {
                const response = await fetch(
                    '/api/execution?symbol=' + encodeURIComponent(selectedSymbol) +
                    '&size=' + encodeURIComponent(executionSize) +
                    '&scenario=' + encodeURIComponent(executionScenario)
                );
                const payload = await response.json();
                const item = payload.execution;
                if (!item) {
                    resetExecution(payload.note);
                    return;
                }
                document.getElementById('exec-route').textContent = item.buy_on + ' ' + t('to') + ' ' + item.sell_on;
                document.getElementById('exec-raw').textContent = percentText(item.raw_spread_pct);
                document.getElementById('exec-vwap').textContent = percentText(item.executable_spread_pct);
                const net = document.getElementById('exec-net');
                net.textContent = formatMoney(item.estimated_net_profit_usd);
                net.className = 'fact-value ' + (item.estimated_net_profit_usd >= 0 ? 'positive' : 'negative');
                document.getElementById('exec-max-size').textContent = item.max_profitable_size.toFixed(4);
                document.getElementById('exec-sync').textContent =
                    item.sync_quality + ' / ' + item.snapshot_skew_ms.toFixed(1) + ' ms';
                document.getElementById('waterfall-raw').textContent = percentText(item.raw_spread_pct);
                document.getElementById('waterfall-vwap').textContent = percentText(item.executable_spread_pct);
                document.getElementById('waterfall-fees').textContent = '-$' + item.estimated_fees_usd.toFixed(2);
                document.getElementById('waterfall-net').textContent = formatMoney(item.estimated_net_profit_usd);
                const maxBar = Math.max(
                    Math.abs(item.raw_spread_pct),
                    Math.abs(item.executable_spread_pct),
                    Math.abs(item.estimated_net_profit_usd / Math.max(1, item.buy_notional_usd) * 100),
                    0.01
                );
                setBar('bar-raw', item.raw_spread_pct, maxBar);
                setBar('bar-vwap', item.executable_spread_pct, maxBar);
                setBar('bar-fees', -item.estimated_fees_usd / Math.max(1, item.buy_notional_usd) * 100, maxBar);
                setBar('bar-net', item.estimated_net_profit_usd / Math.max(1, item.buy_notional_usd) * 100, maxBar);
                renderFillRows('buy-book-rows', item.buy_fills);
                renderFillRows('sell-book-rows', item.sell_fills);
                document.getElementById('buy-book-title').textContent = t('buyAsksOn') + ' ' + item.buy_on;
                document.getElementById('sell-book-title').textContent = t('sellBidsOn') + ' ' + item.sell_on;
                const verdict = document.getElementById('exec-verdict');
                const good = item.estimated_net_profit_usd > 0 && item.fill_ratio >= 1 && item.combined_slippage_pct < 0.2;
                const risky = item.estimated_net_profit_usd > 0 && item.fill_ratio >= 1;
                verdict.className = 'verdict ' + (good ? 'good' : risky ? 'risky' : 'bad');
                document.getElementById('exec-verdict-value').textContent = good ? t('executable') : risky ? t('risky') : t('rejected');
                document.getElementById('exec-verdict-detail').textContent =
                    t('scoreLabel') + ' ' + item.score.toFixed(1) + '/100. ' +
                    t('fillLabel') + ' ' + (item.fill_ratio * 100).toFixed(1) + '%. ' +
                    t('slippageLabel') + ' ' + item.combined_slippage_pct.toFixed(4) + '%. ' +
                    t('snapshotSkewLabel') + ' ' + item.snapshot_skew_ms.toFixed(1) + ' ' + t('ms') + '. ' +
                    (item.score_reasons || []).slice(0, 2).map(translateReason).join(' ');
            } catch (error) {
                console.error('Failed to load execution estimate', error);
            }
        };

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(protocol + '//' + window.location.host + '/ws');

        ws.onopen = () => {
            document.getElementById('ws-status').textContent = t('connected');
            document.getElementById('ws-dot').className = 'dot live';
        };

        ws.onclose = () => {
            document.getElementById('ws-status').textContent = t('disconnected');
            document.getElementById('ws-dot').className = 'dot';
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            const symbolData = data.symbols[selectedSymbol];
            if (!symbolData) {
                return;
            }

            renderRows(symbolData.exchanges);

            const spreadEl = document.getElementById('spread');
            if (symbolData.spread !== null) {
                spreadEl.textContent = (symbolData.spread > 0 ? '+$' : '-$') + Math.abs(symbolData.spread).toFixed(2);
                spreadEl.className = 'metric-value ' + (symbolData.spread > 0 ? 'positive' : 'negative');
                document.getElementById('spread-route').textContent = symbolData.route;
            } else {
                spreadEl.textContent = t('waiting');
                spreadEl.className = 'metric-value';
                document.getElementById('spread-route').textContent = t('noFreshRoute');
            }

            document.getElementById('fresh-count').textContent = symbolData.fresh_count + ' / ' + symbolData.exchange_count;
            document.getElementById('last-update').textContent = data.time;
            updateOpportunity();
            updateHistory();
            updateExecution();
        };
