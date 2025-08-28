/**
 * LoggerUtils - Centralizacja inicjalizacji loggerów
 * Eliminuje powtarzalny kod inicjalizacji loggera w każdym module
 */
import { logger, LogLevel } from "../logger.js";
import { LOG_LEVEL } from '../config.js';
/**
 * Tworzy obiekt loggera dla modułu z predefiniowanymi metodami
 * @param {string} moduleName - Nazwa modułu
 * @returns {Logger} Obiekt z metodami logowania
 */
export function createModuleLogger(moduleName) {
    logger.setModuleLevel(moduleName, LogLevel[LOG_LEVEL]);
    return {
        debug: (...args) => logger.debug(moduleName, ...args),
        info: (...args) => logger.info(moduleName, ...args),
        warn: (...args) => logger.warn(moduleName, ...args),
        error: (...args) => logger.error(moduleName, ...args)
    };
}
/**
 * Tworzy logger z automatycznym wykrywaniem nazwy modułu z URL
 * @returns {Logger} Obiekt z metodami logowania
 */
export function createAutoLogger() {
    const stack = new Error().stack;
    const match = stack?.match(/\/([^\/]+)\.js/);
    const moduleName = match ? match[1] : 'Unknown';
    return createModuleLogger(moduleName);
}
/**
 * Wrapper dla operacji z automatycznym logowaniem błędów
 * @param {Function} operation - Operacja do wykonania
 * @param {Logger} log - Obiekt loggera
 * @param {string} operationName - Nazwa operacji (dla logów)
 * @returns {Function} Opakowana funkcja
 */
export function withErrorLogging(operation, log, operationName) {
    return async function (...args) {
        try {
            log.debug(`Starting ${operationName}`);
            const result = await operation.apply(this, args);
            log.debug(`Completed ${operationName}`);
            return result;
        }
        catch (error) {
            log.error(`Error in ${operationName}:`, error);
            throw error;
        }
    };
}
/**
 * Decorator dla metod klasy z automatycznym logowaniem
 * @param {Logger} log - Obiekt loggera
 * @param {string} methodName - Nazwa metody
 */
export function logMethod(log, methodName) {
    return function (target, propertyKey, descriptor) {
        const originalMethod = descriptor.value;
        descriptor.value = async function (...args) {
            try {
                log.debug(`${methodName || propertyKey} started`);
                const result = await originalMethod.apply(this, args);
                log.debug(`${methodName || propertyKey} completed`);
                return result;
            }
            catch (error) {
                log.error(`${methodName || propertyKey} failed:`, error);
                throw error;
            }
        };
        return descriptor;
    };
}
