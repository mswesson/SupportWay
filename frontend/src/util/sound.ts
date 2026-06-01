// Звуковое уведомление о новом зарезервированном чате — короткий бип через Web Audio.
// Без аудио-файлов: генерируем сигнал осциллятором.

let audioCtx: AudioContext | null = null;

/** Лениво создаёт/возобновляет AudioContext (нужен пользовательский жест — логин подходит). */
function getContext(): AudioContext | null {
  try {
    if (!audioCtx) {
      const Ctx = window.AudioContext || (window as any).webkitAudioContext;
      if (!Ctx) return null;
      audioCtx = new Ctx();
    }
    if (audioCtx.state === 'suspended') {
      void audioCtx.resume();
    }
    return audioCtx;
  } catch {
    return null;
  }
}

/** Проигрывает короткий двухтоновый сигнал уведомления. */
export function playNotificationBeep(): void {
  const ctx = getContext();
  if (!ctx) return;

  const now = ctx.currentTime;
  const gain = ctx.createGain();
  gain.connect(ctx.destination);
  // Плавная огибающая, чтобы не было щелчков.
  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.exponentialRampToValueAtTime(0.15, now + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.35);

  const osc = ctx.createOscillator();
  osc.type = 'sine';
  osc.frequency.setValueAtTime(880, now); // нота A5
  osc.frequency.setValueAtTime(1320, now + 0.16); // выше — двухтоновый «динь-динь»
  osc.connect(gain);
  osc.start(now);
  osc.stop(now + 0.36);
}
