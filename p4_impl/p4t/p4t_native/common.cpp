#include "common.h"
#include "spdlog/sinks/sink.h"

namespace {

auto sink() -> std::shared_ptr<spdlog::sinks::sink> const& {
    static auto initialized = false;    
    static std::shared_ptr<spdlog::sinks::sink> sink{};

    if (!initialized) {
        sink = std::make_shared<spdlog::sinks::simple_file_sink_mt>("logs/p4t_opt.log");
        initialized = true;
    }

    return sink;
}


};

auto p4t::log() -> std::shared_ptr<spdlog::logger> const& {
    static auto initialized = false;
    static std::shared_ptr<spdlog::logger> logger{};

    if (!initialized) {
        logger = std::make_shared<spdlog::logger>("logger", sink());
        logger->flush_on(spdlog::level::info);
        initialized = true;
    }
    return logger;
}

auto p4t::python_log() -> std::shared_ptr<spdlog::logger> const& {
    static auto initialized = false;
    static std::shared_ptr<spdlog::logger> logger{};

    if (!initialized) {
        logger = std::make_shared<spdlog::logger>("python", sink());
        logger->flush_on(spdlog::level::info);
        initialized = true;
    }
    return logger;
}
