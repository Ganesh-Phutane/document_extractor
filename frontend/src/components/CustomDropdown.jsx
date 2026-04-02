import React, { useState } from 'react';
import { ChevronDown, Loader2, FileText } from 'lucide-react';
import '../styles/components/CustomDropdown.css';

/**
 * A reusable, styled dropdown component that matches the Azure extraction UI.
 * 
 * @param {Object} props
 * @param {string} props.label - Optional label for the form group
 * @param {Array} props.options - Array of option objects
 * @param {string|number} props.value - Currently selected option ID
 * @param {Function} props.onChange - Callback when an option is selected: (id) => void
 * @param {string} props.placeholder - Placeholder text when no option is selected
 * @param {boolean} props.loading - Shows a loader in the header
 * @param {boolean} props.disabled - Disables interaction
 * @param {React.ElementType} props.icon - Default icon for options (default: FileText)
 * @param {Function} props.getLabel - Function to get display label from option (default: opt.filename || opt.name)
 * @param {Function} props.getSublabel - Function to get sub-details from option (optional)
 * @param {string} props.className - Additional class for the container
 */
const CustomDropdown = ({
  label,
  options = [],
  value,
  onChange,
  placeholder = '-- Select --',
  loading = false,
  disabled = false,
  icon: Icon = FileText,
  getLabel = (opt) => opt.filename || opt.name || opt.label,
  getSublabel,
  className = ''
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const selectedOption = options.find(opt => opt.id === value);

  const handleToggle = () => {
    if (!disabled && !loading) {
      setIsOpen(!isOpen);
    }
  };

  const handleSelect = (option) => {
    onChange(option.id);
    setIsOpen(false);
  };

  return (
    <div className={`form-group ${className}`}>
      {label && <label>{label}</label>}
      <div className="custom-dropdown-container">
        <div 
          className={`custom-dropdown-header ${isOpen ? 'open' : ''} ${disabled || loading ? 'disabled' : ''}`}
          onClick={handleToggle}
        >
          <div className="selected-value">
            {selectedOption ? (
              <>
                <Icon size={16} className="text-muted" />
                <span>{getLabel(selectedOption)} {getSublabel ? getSublabel(selectedOption) : ''}</span>
              </>
            ) : (
              <span className="placeholder">{placeholder}</span>
            )}
          </div>
          <ChevronDown className={`dropdown-arrow ${isOpen ? 'rotated' : ''}`} size={18} />
          {loading && <Loader2 className="animate-spin dropdown-loader" size={16} />}
        </div>

        {isOpen && (
          <div className="custom-dropdown-options glass shadow-lg">
            <div className="options-scroll-area">
              {options.length === 0 ? (
                <div className="no-options">No options available</div>
              ) : (
                options.map(option => (
                  <div 
                    key={option.id} 
                    className={`dropdown-option ${value === option.id ? 'active' : ''}`}
                    onClick={() => handleSelect(option)}
                  >
                    <Icon size={14} className="text-muted" />
                    <div className="option-details">
                      <span className="option-name">{getLabel(option)}</span>
                      {getSublabel && (
                        <span className="option-size">{getSublabel(option)}</span>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
        
        {isOpen && <div className="dropdown-overlay" onClick={() => setIsOpen(false)} />}
      </div>
    </div>
  );
};

export default CustomDropdown;
