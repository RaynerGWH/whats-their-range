// WTR bridge, AGPL-3.0-or-later. Upstream sources in vendor/ are unmodified.
#include "aiengine4.h"
#include "tools.h"
#include <cmath>
#include <cstdint>
#include <iostream>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>

static std::mt19937_64 rng;
void Tools::GetRand(int low, int high, unsigned count, int* out) {
    if (low < 0 || high < low || count > 1024) throw std::runtime_error("rng bounds");
    // Rejection sampling avoids library-specific uniform_int_distribution behavior.
    const uint64_t bound = uint64_t(high) - low + 1;
    const uint64_t threshold = -bound % bound;
    for (unsigned i = 0; i < count; ++i) {
        uint64_t value;
        do { value = rng(); } while (value < threshold);
        out[i] = low + int(value % bound);
    }
}

int main(int argc, char** argv) {
    if (argc == 2 && std::string(argv[1]) == "--version") {
        std::cout << "wtr-pokerth-1 0a7dceb575d8b9dfcbd7c46ec7a90482cbdb40ba\n";
        return 0;
    }
    try {
        std::string input;
        char ch;
        while (std::cin.get(ch) && ch != '\n') {
            if (input.size() >= 1024) throw std::runtime_error("input size");
            input += ch;
        }
        std::istringstream in(input);
        uint64_t seed;
        AiSituation s{};
        AiPersonality p;
        int bigBlindFlag;
        if (!(in >> seed >> s.round >> s.holeCards[0] >> s.holeCards[1]))
            throw std::runtime_error("fields");
        s.boardSize = s.round == 0 ? 0 : s.round + 2;
        if (s.round < 0 || s.round > 3) throw std::runtime_error("street");
        for (int i = 0; i < s.boardSize; ++i) {
            if (!(in >> s.boardCards[i])) throw std::runtime_error("board");
        }
        if (!(in >> s.myCash >> s.mySet >> s.highestSet >> s.minimumRaise
              >> s.smallBlind >> s.potBefore >> s.setsThisRound >> s.opponents
              >> s.opponentsBehind >> s.effectiveOpponentCash >> s.raisesThisRound
              >> bigBlindFlag >> s.opponentVpipPercent >> s.opponentAggressionPercent
              >> p.looseness >> p.aggression >> p.bluffRate))
            throw std::runtime_error("fields");
        in >> std::ws;
        if (!in.eof()) throw std::runtime_error("extra fields");
        uint64_t seen = 0;
        for (int i = 0; i < 2 + s.boardSize; ++i) {
            const int c = i < 2 ? s.holeCards[i] : s.boardCards[i - 2];
            if (c < 0 || c > 51 || (seen & (1ULL << c))) throw std::runtime_error("cards");
            seen |= 1ULL << c;
        }
        for (int n : {s.myCash, s.mySet, s.highestSet, s.minimumRaise, s.smallBlind,
                      s.potBefore, s.setsThisRound, s.effectiveOpponentCash})
            if (n < 0 || n > 10000000) throw std::runtime_error("chips");
        if (s.myCash == 0 || s.smallBlind == 0 || s.minimumRaise == 0 ||
            s.highestSet < s.mySet || s.setsThisRound < s.highestSet ||
            s.opponents < 1 || s.opponents > 5 || s.opponentsBehind < 0 ||
            s.opponentsBehind > s.opponents || s.raisesThisRound < 0 ||
            s.raisesThisRound > 1000 || bigBlindFlag < 0 || bigBlindFlag > 1)
            throw std::runtime_error("situation");
        for (int n : {s.opponentVpipPercent, s.opponentAggressionPercent})
            if (n < -1 || n > 100) throw std::runtime_error("statistics");
        for (double n : {p.looseness, p.aggression, p.bluffRate})
            if (!std::isfinite(n) || n < 0.25 || n > 2.0) throw std::runtime_error("personality");
        s.amBigBlind = bigBlindFlag;
        rng.seed(seed);
        const auto d = AiEngine4::decide(s, p);
        if (d.action < PLAYER_ACTION_FOLD || d.action > PLAYER_ACTION_ALLIN || d.bet < 0 || d.raise < 0)
            throw std::runtime_error("decision");
        std::cout << int(d.action) << ' ' << d.bet << ' ' << d.raise << '\n';
    } catch (...) {
        // Never echo private inputs or native exceptions into logs.
        std::cerr << "PokerTH bridge rejected input or decision\n";
        return 2;
    }
}
