% runMetric1.m
function json_output = runMetric1(input_scid, input_metric, input_threshold)
    % Generate time series data at 0.1 Hz for 5 minutes
    % 0.1 Hz = 1 sample every 10 seconds
    % 5 minutes = 300 seconds = 30 samples
    
    % Generate timestamps and values
    startTime = now;
    for i = 1:30
        % Calculate timestamp (10 seconds apart)
        currentTime = startTime + (i-1)/(24*3600*0.1); % 0.1 Hz = 1 sample per 10 seconds
        data.time(i) = currentTime;  % Store as datenum
        
        % Generate random value between 0 and 1
        data.value(i) = rand()*30;
    end
    
    % Find threshold crossings
    breach_trigger = find(data.value > input_threshold);
    
    % Get breach data
    breach_times = data.time(breach_trigger);
    breach_values = data.value(breach_trigger);
    
    % Convert to JSON and write to file
    json_output = writeMetricToJson(breach_times, breach_values, input_scid, input_metric, input_threshold);
end


