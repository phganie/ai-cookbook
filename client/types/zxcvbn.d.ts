declare module 'zxcvbn' {
  export interface ZxcvbnResult {
    score: 0 | 1 | 2 | 3 | 4;
    feedback: {
      warning: string;
      suggestions: string[];
    };
    crack_times_seconds: {
      offline_fast_hashing_1e10_per_second: number;
      offline_slow_hashing_1e4_per_second: number;
      online_no_throttling_10_per_second: number;
      online_throttling_100_per_hour: number;
    };
    crack_times_display: {
      offline_fast_hashing_1e10_per_second: string;
      offline_slow_hashing_1e4_per_second: string;
      online_no_throttling_10_per_second: string;
      online_throttling_100_per_hour: string;
    };
    calc_time: number;
  }

  function zxcvbn(password: string): ZxcvbnResult;
  export default zxcvbn;
}

