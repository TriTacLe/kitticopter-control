% Builds the kitticopter Simulink model from the session 1 numbers.
% Run this once, it creates and opens kitticopter.slx

% The plant is set by the aerodynamic constant b. A = a/b and T = 1/b, so one
% error in b moves both, and A*T goes as the square of it. Scale b, not T.
a = 2.4322;      % m/(V s^2), thrust constant, fixed
b = 0.10485;     % 1/s, aerodynamic drag, the thing with 10 percent uncertainty
bscale = 1.0;    % set 0.9 or 1.1 to visit the robustness corners

b = b * bscale;
A = a / b;       % 23.196 nominal, 25.774 at b -10%, 21.089 at b +10%
T = 1 / b;       % 9.537 nominal, 10.597 at b -10%, 8.670 at b +10%
k = 0.95;        % V/m, sensor
Vhover = 2.5;    % V
Kp = 0.005;      % window 0.005 to 0.006, trimmed on the bench
setpoint = 7;    % m, capped by the sensor saturating at 10.5 m

zeta = 1 / (2*sqrt(Kp*k*A*T));
wn   = sqrt(Kp*k*A/T);
fprintf('b %+.0f%%: A = %.3f, T = %.3f, zeta = %.3f, wn = %.4f, OS = %.1f %%\n', ...
        (bscale-1)*100, A, T, zeta, wn, 100*exp(-pi*zeta/sqrt(1-zeta^2)));

name = 'kitticopter';
if bdIsLoaded(name)
    close_system(name, 0)
end
new_system(name)
open_system(name)

add_block('simulink/Sources/Step', [name '/Setpoint'], ...
    'Time','5', 'Before','0', 'After','7', 'Position',[30 100 60 130])

add_block('simulink/Math Operations/Gain', [name '/k ref'], ...
    'Gain','k', 'Position',[100 100 130 130])

add_block('simulink/Math Operations/Sum', [name '/Error'], ...
    'Inputs','+-', 'Position',[170 100 190 130])

add_block('simulink/Math Operations/Gain', [name '/Kp'], ...
    'Gain','Kp', 'Position',[220 100 250 130])

add_block('simulink/Sources/Constant', [name '/Hover bias'], ...
    'Value','Vhover', 'Position',[220 180 250 210])

add_block('simulink/Math Operations/Sum', [name '/Add bias'], ...
    'Inputs','++', 'Position',[290 100 310 130])

% the plant only accepts 0 to 5 V, this is the limit that bites
add_block('simulink/Discontinuities/Saturation', [name '/0 to 5 V'], ...
    'UpperLimit','5', 'LowerLimit','0', 'Position',[340 100 370 130])

add_block('simulink/Math Operations/Sum', [name '/Gravity'], ...
    'Inputs','+-', 'Position',[400 100 420 130])

add_block('simulink/Sources/Constant', [name '/g'], ...
    'Value','Vhover', 'Position',[340 180 370 210])

% velocity side of the plant, A/(Ts+1)
add_block('simulink/Continuous/Transfer Fcn', [name '/Plant'], ...
    'Numerator','A', 'Denominator','[T 1]', 'Position',[450 95 520 135])

% velocity integrates to height
add_block('simulink/Continuous/Integrator', [name '/Height'], ...   
    'Position',[550 100 580 130])

add_block('simulink/Sinks/Scope', [name '/Scope'], ...
    'Position',[700 100 730 130])

add_block('simulink/Math Operations/Gain', [name '/k sensor'], ...
    'Gain','k', 'Position',[550 200 580 230])

add_line(name, 'Setpoint/1', 'k ref/1')
add_line(name, 'k ref/1', 'Error/1')
add_line(name, 'Error/1', 'Kp/1')
add_line(name, 'Kp/1', 'Add bias/1')
add_line(name, 'Hover bias/1', 'Add bias/2')
add_line(name, 'Add bias/1', '0 to 5 V/1')
add_line(name, '0 to 5 V/1', 'Gravity/1')
add_line(name, 'g/1', 'Gravity/2')
add_line(name, 'Gravity/1', 'Plant/1')
add_line(name, 'Plant/1', 'Height/1')
add_line(name, 'Height/1', 'Scope/1')
add_line(name, 'Height/1', 'k sensor/1', 'autorouting','on')
add_line(name, 'k sensor/1', 'Error/2', 'autorouting','on')

set_param(name, 'StopTime','200')
save_system(name)

fprintf('built %s.slx with A = %.1f, T = %.1f, k = %.2f, Kp = %.4f\n', name, A, T, k, Kp);
